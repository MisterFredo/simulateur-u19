import streamlit as st
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account

# Configuration
st.set_page_config(page_title="Simulation What If", layout="wide")

# Connexion BigQuery
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"]
)
client = bigquery.Client(credentials=credentials, project=credentials.project_id)

# Chargement des championnats
@st.cache_data(show_spinner=False)
def load_championnats():
    query = """
        SELECT ID_CHAMPIONNAT, NOM_CHAMPIONNAT, CATEGORIE, NIVEAU
        FROM `datafoot-448514.DATAFOOT.DATAFOOT_CHAMPIONNAT`
        ORDER BY CATEGORIE, NIVEAU, NOM_CHAMPIONNAT
    """
    return client.query(query).to_dataframe()

championnats_df = load_championnats()

# Chargement des pénalités
@st.cache_data(show_spinner=False)
def load_penalites():
    query = """
        SELECT ID_EQUIPE, ID_CHAMPIONNAT, POULE, POINTS, DATE
        FROM `datafoot-448514.DATAFOOT.DATAFOOT_PENALITE`
    """
    return client.query(query).to_dataframe()

# Filtres
st.sidebar.header("Filtres simulation")
selected_categorie = st.sidebar.selectbox("Catégorie", sorted(championnats_df["CATEGORIE"].unique()))
selected_niveau = st.sidebar.selectbox(
    "Niveau", sorted(championnats_df[championnats_df["CATEGORIE"] == selected_categorie]["NIVEAU"].unique())
)
champ_options = championnats_df[
    (championnats_df["CATEGORIE"] == selected_categorie) &
    (championnats_df["NIVEAU"] == selected_niveau)
]
selected_nom = st.sidebar.selectbox("Championnat", champ_options["NOM_CHAMPIONNAT"])
champ_id = champ_options[champ_options["NOM_CHAMPIONNAT"] == selected_nom]["ID_CHAMPIONNAT"].values[0]

# Sélecteur de poule
@st.cache_data(show_spinner=False)
def get_poules(champ_id):
    query = f"""
        SELECT DISTINCT POULE
        FROM `datafoot-448514.DATAFOOT.DATAFOOT_MATCH_2025`
        WHERE ID_CHAMPIONNAT = {champ_id} AND POULE IS NOT NULL
        ORDER BY POULE
    """
    return client.query(query).to_dataframe()

poules_df = get_poules(champ_id)
all_poules = sorted(poules_df["POULE"].dropna().unique())
if len(all_poules) > 1:
    selected_poule = st.sidebar.selectbox("Poule", ["Toutes les poules"] + all_poules)
else:
    selected_poule = all_poules[0] if all_poules else "Toutes les poules"

date_limite = st.sidebar.date_input("Date max à prendre en compte", value=pd.to_datetime("2025-03-31"))

# Affichage des matchs modifiables
st.title("🧪 Simulation What If")

filtrer_non_joues = st.checkbox("Afficher uniquement les matchs non joués", value=True)

@st.cache_data(show_spinner=False)
def get_matchs_modifiables(champ_id, date_limite, non_joues_only):
    condition = "AND STATUT IS NULL" if non_joues_only else ""
    query = f"""
        SELECT 
            ID_MATCH,
            JOURNEE,
            POULE,
            DATE,
            EQUIPE_DOM,
            NB_BUT_DOM,
            EQUIPE_EXT,
            NB_BUT_EXT,
            STATUT
        FROM `datafoot-448514.DATAFOOT.DATAFOOT_MATCH_2025`
        WHERE ID_CHAMPIONNAT = {champ_id}
          AND DATE <= DATE('{date_limite}')
          {condition}
        ORDER BY DATE, JOURNEE
    """
    return client.query(query).to_dataframe()

matchs_simulables = get_matchs_modifiables(champ_id, date_limite, filtrer_non_joues)
if selected_poule != "Toutes les poules":
    matchs_simulables = matchs_simulables[matchs_simulables["POULE"] == selected_poule]

if matchs_simulables.empty:
    st.info("Aucun match à afficher pour cette configuration.")
else:
    st.markdown("### Matchs simulables")
    df_simulation = matchs_simulables.copy()
    edited_df = st.data_editor(
        df_simulation[["ID_MATCH", "JOURNEE", "POULE", "DATE", "EQUIPE_DOM", "NB_BUT_DOM", "EQUIPE_EXT", "NB_BUT_EXT", "STATUT"]],
        num_rows="dynamic",
        use_container_width=True,
        key="simulation_scores"
    )
    if st.button("🔁 Recalculer le classement avec ces scores simulés"):
        st.session_state["simulated_scores"] = edited_df
        st.success("Scores pris en compte. On peut maintenant recalculer le classement.")

        @st.cache_data(show_spinner=False)
def get_matchs_termines(champ_id, date_limite):
    query = f"""
        SELECT ID_MATCH, JOURNEE, POULE, DATE, EQUIPE_DOM, NB_BUT_DOM, EQUIPE_EXT, NB_BUT_EXT, STATUT
        FROM `datafoot-448514.DATAFOOT.DATAFOOT_MATCH_2025`
        WHERE ID_CHAMPIONNAT = {champ_id}
          AND DATE <= DATE('{date_limite}')
          AND STATUT = 'TERMINE'
    """
    return client.query(query).to_dataframe()


        # 🔢 Recalcul du classement avec scores simulés + pénalités
        matchs_termines = get_matchs_termines(champ_id, date_limite)

        df_simules = df_valid.set_index("ID_MATCH")
        matchs_termines = matchs_termines.set_index("ID_MATCH")
        matchs_reels_sans_doublon = matchs_termines[~matchs_termines.index.isin(df_simules.index)]
        matchs_complets = pd.concat([matchs_reels_sans_doublon, df_simules]).reset_index()

        dom = matchs_complets.rename(columns={
            "ID_EQUIPE_DOM": "ID_EQUIPE",
            "EQUIPE_DOM": "NOM_EQUIPE",
            "NB_BUT_DOM": "BUTS_POUR",
            "NB_BUT_EXT": "BUTS_CONTRE"
        })
        dom["POINTS"] = dom.apply(lambda r: 3 if r.BUTS_POUR > r.BUTS_CONTRE else (1 if r.BUTS_POUR == r.BUTS_CONTRE else 0), axis=1)

        ext = matchs_complets.rename(columns={
            "ID_EQUIPE_EXT": "ID_EQUIPE",
            "EQUIPE_EXT": "NOM_EQUIPE",
            "NB_BUT_EXT": "BUTS_POUR",
            "NB_BUT_DOM": "BUTS_CONTRE"
        })
        ext["POINTS"] = ext.apply(lambda r: 3 if r.BUTS_POUR > r.BUTS_CONTRE else (1 if r.BUTS_POUR == r.BUTS_CONTRE else 0), axis=1)

        full = pd.concat([dom, ext])["POULE", "ID_EQUIPE", "NOM_EQUIPE", "BUTS_POUR", "BUTS_CONTRE", "POINTS"]

        classement = full.groupby(["POULE", "ID_EQUIPE", "NOM_EQUIPE"]).agg(
            MJ=("POINTS", "count"),
            G=("POINTS", lambda x: (x == 3).sum()),
            N=("POINTS", lambda x: (x == 1).sum()),
            P=("POINTS", lambda x: (x == 0).sum()),
            BP=("BUTS_POUR", "sum"),
            BC=("BUTS_CONTRE", "sum"),
            PTS=("POINTS", "sum")
        ).reset_index()

        classement["DIFF"] = classement["BP"] - classement["BC"]

        # Ajout des pénalités
        penalites_actives = penalites_df[
            (penalites_df["ID_CHAMPIONNAT"] == champ_id) &
            (penalites_df["DATE"] <= pd.to_datetime(date_limite))
        ]
        penalites_par_equipe = penalites_actives.groupby("ID_EQUIPE")["POINTS"].sum().reset_index()
        penalites_par_equipe.rename(columns={"POINTS": "PENALITES"}, inplace=True)

        classement = classement.merge(penalites_par_equipe, on="ID_EQUIPE", how="left")
        classement["PENALITES"] = classement["PENALITES"].fillna(0).astype(int)
        classement["POINTS"] = classement["PTS"] - classement["PENALITES"]

        classement = classement.sort_values(by=["POULE", "POINTS", "DIFF", "BP"], ascending=[True, False, False, False])
        classement["CLASSEMENT"] = classement.groupby("POULE").cumcount() + 1

        if selected_poule != "Toutes les poules":
            classement = classement[classement["POULE"] == selected_poule]

        for poule in sorted(classement["POULE"].unique()):
            st.subheader(f"Poule {poule}")
            df = classement[classement["POULE"] == poule][[
                "CLASSEMENT", "NOM_EQUIPE", "POINTS", "PENALITES", "BP", "BC", "DIFF", "MJ"
            ]].rename(columns={
                "BP": "BUTS_POUR",
                "BC": "BUTS_CONTRE",
                "MJ": "MATCHS_JOUES"
            })
            st.dataframe(df, use_container_width=True)

# Cas particuliers (U19 / U17 / N2 / N3)
if "simulated_scores" in st.session_state and "classement" in locals() and selected_poule == "Toutes les poules":
    if champ_id == 6 and not classement.empty:
        st.markdown("### 🚨 Classement spécial des 11èmes (règle U19 National)")
        df_11e = classement[classement["CLASSEMENT"] == 11]
        comparatif_11e = []

        for _, row in df_11e.iterrows():
            poule = row["POULE"]
            equipe = row["NOM_EQUIPE"]
            adversaires = classement[
                (classement["POULE"] == poule) &
                (classement["CLASSEMENT"].between(6, 10))
            ]["NOM_EQUIPE"].tolist()

            confrontations = matchs_complets[
                ((matchs_complets["EQUIPE_DOM"] == equipe) & (matchs_complets["EQUIPE_EXT"].isin(adversaires))) |
                ((matchs_complets["EQUIPE_EXT"] == equipe) & (matchs_complets["EQUIPE_DOM"].isin(adversaires)))
            ]

            pts = 0
            for _, m in confrontations.iterrows():
                if m["EQUIPE_DOM"] == equipe:
                    if m["NB_BUT_DOM"] > m["NB_BUT_EXT"]: pts += 3
                    elif m["NB_BUT_DOM"] == m["NB_BUT_EXT"]: pts += 1
                elif m["EQUIPE_EXT"] == equipe:
                    if m["NB_BUT_EXT"] > m["NB_BUT_DOM"]: pts += 3
                    elif m["NB_BUT_EXT"] == m["NB_BUT_DOM"]: pts += 1

            comparatif_11e.append({"POULE": poule, "EQUIPE": equipe, "PTS_CONFRONT_6_10": pts})

        df_11e_comp = pd.DataFrame(comparatif_11e).sort_values("PTS_CONFRONT_6_10")
        df_11e_comp["RANG"] = df_11e_comp["PTS_CONFRONT_6_10"].rank(method="min")
        st.dataframe(df_11e_comp, use_container_width=True)

    if champ_id == 7 and not classement.empty:
        st.markdown("### 🥈 Comparatif des 2e (règle U17 National)")
        df_2e = classement[classement["CLASSEMENT"] == 2]
        comparatif_2e = []

        for _, row in df_2e.iterrows():
            poule = row["POULE"]
            equipe = row["NOM_EQUIPE"]
            adversaires = classement[
                (classement["POULE"] == poule) &
                (classement["CLASSEMENT"].between(1, 5))
            ]["NOM_EQUIPE"].tolist()

            confrontations = matchs_complets[
                ((matchs_complets["EQUIPE_DOM"] == equipe) & (matchs_complets["EQUIPE_EXT"].isin(adversaires))) |
                ((matchs_complets["EQUIPE_EXT"] == equipe) & (matchs_complets["EQUIPE_DOM"].isin(adversaires)))
            ]

            pts = 0
            for _, m in confrontations.iterrows():
                if m["EQUIPE_DOM"] == equipe:
                    if m["NB_BUT_DOM"] > m["NB_BUT_EXT"]: pts += 3
                    elif m["NB_BUT_DOM"] == m["NB_BUT_EXT"]: pts += 1
                elif m["EQUIPE_EXT"] == equipe:
                    if m["NB_BUT_EXT"] > m["NB_BUT_DOM"]: pts += 3
                    elif m["NB_BUT_EXT"] == m["NB_BUT_DOM"]: pts += 1

            comparatif_2e.append({"POULE": poule, "EQUIPE": equipe, "PTS_CONFRONT_TOP5": pts})

        df_2e_comp = pd.DataFrame(comparatif_2e).sort_values("PTS_CONFRONT_TOP5", ascending=False)
        df_2e_comp["RANG"] = df_2e_comp["PTS_CONFRONT_TOP5"].rank(method="min", ascending=False)
        st.dataframe(df_2e_comp, use_container_width=True)

    if champ_id == 4 and not classement.empty:
        st.markdown("### 🔻 Comparatif des 13e (règle N2)")
        df_13e = classement[classement["CLASSEMENT"] == 13]
        comparatif_13e = []

        for _, row in df_13e.iterrows():
            poule = row["POULE"]
            equipe = row["NOM_EQUIPE"]
            adversaires = classement[
                (classement["POULE"] == poule) &
                (classement["CLASSEMENT"].between(8, 12))
            ]["NOM_EQUIPE"].tolist()

            confrontations = matchs_complets[
                ((matchs_complets["EQUIPE_DOM"] == equipe) & (matchs_complets["EQUIPE_EXT"].isin(adversaires))) |
                ((matchs_complets["EQUIPE_EXT"] == equipe) & (matchs_complets["EQUIPE_DOM"].isin(adversaires)))
            ]

            pts = 0
            for _, m in confrontations.iterrows():
                if m["EQUIPE_DOM"] == equipe:
                    if m["NB_BUT_DOM"] > m["NB_BUT_EXT"]: pts += 3
                    elif m["NB_BUT_DOM"] == m["NB_BUT_EXT"]: pts += 1
                elif m["EQUIPE_EXT"] == equipe:
                    if m["NB_BUT_EXT"] > m["NB_BUT_DOM"]: pts += 3
                    elif m["NB_BUT_EXT"] == m["NB_BUT_DOM"]: pts += 1

            comparatif_13e.append({"POULE": poule, "EQUIPE": equipe, "PTS_CONFRONT_8_12": pts})

        df_13e_comp = pd.DataFrame(comparatif_13e).sort_values("PTS_CONFRONT_8_12", ascending=False)
        df_13e_comp["RANG"] = df_13e_comp["PTS_CONFRONT_8_12"].rank(method="min", ascending=False)
        st.dataframe(df_13e_comp, use_container_width=True)

    if champ_id == 5 and not classement.empty:
        st.markdown("### 🔻 Comparatif des 10e (règle N3)")
        df_10e = classement[classement["CLASSEMENT"] == 10]
        comparatif_10e = []

        for _, row in df_10e.iterrows():
            poule = row["POULE"]
            equipe = row["NOM_EQUIPE"]
            adversaires = classement[
                (classement["POULE"] == poule) &
                (classement["CLASSEMENT"].between(5, 9))
            ]["NOM_EQUIPE"].tolist()

            confrontations = matchs_complets[
                ((matchs_complets["EQUIPE_DOM"] == equipe) & (matchs_complets["EQUIPE_EXT"].isin(adversaires))) |
                ((matchs_complets["EQUIPE_EXT"] == equipe) & (matchs_complets["EQUIPE_DOM"].isin(adversaires)))
            ]

            pts = 0
            for _, m in confrontations.iterrows():
                if m["EQUIPE_DOM"] == equipe:
                    if m["NB_BUT_DOM"] > m["NB_BUT_EXT"]: pts += 3
                    elif m["NB_BUT_DOM"] == m["NB_BUT_EXT"]: pts += 1
                elif m["EQUIPE_EXT"] == equipe:
                    if m["NB_BUT_EXT"] > m["NB_BUT_DOM"]: pts += 3
                    elif m["NB_BUT_EXT"] == m["NB_BUT_DOM"]: pts += 1

            comparatif_10e.append({"POULE": poule, "EQUIPE": equipe, "PTS_CONFRONT_5_9": pts})

        df_10e_comp = pd.DataFrame(comparatif_10e).sort_values("PTS_CONFRONT_5_9", ascending=False)
        df_10e_comp["RANG"] = df_10e_comp["PTS_CONFRONT_5_9"].rank(method="min", ascending=False)
        st.dataframe(df_10e_comp, use_container_width=True)

else:
    if champ_id in [4, 5, 6, 7]:
        st.info("🔒 Les règles spécifiques (U19, U17, N2, N3) ne sont disponibles que si toutes les poules sont affichées.")
