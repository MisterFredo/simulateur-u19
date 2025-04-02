# Nouveau simulateur_whatif.py corrigé
import streamlit as st
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account

st.set_page_config(page_title="Simulation What If", layout="wide")

# Connexion BigQuery
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"]
)
client = bigquery.Client(credentials=credentials, project=credentials.project_id)

# --- Chargement des données de base ---
@st.cache_data(show_spinner=False)
def load_championnats():
    query = """
        SELECT ID_CHAMPIONNAT, NOM_CHAMPIONNAT, CATEGORIE, NIVEAU
        FROM `datafoot-448514.DATAFOOT.DATAFOOT_CHAMPIONNAT`
        ORDER BY CATEGORIE, NIVEAU, NOM_CHAMPIONNAT
    """
    return client.query(query).to_dataframe()

@st.cache_data(show_spinner=False)
def load_penalites():
    query = """
        SELECT ID_EQUIPE, ID_CHAMPIONNAT, POINTS, DATE
        FROM `datafoot-448514.DATAFOOT.DATAFOOT_PENALITE`
    """
    return client.query(query).to_dataframe()

@st.cache_data(show_spinner=False)
def get_matchs(champ_id, date_limite):
    query = f"""
        SELECT ID_MATCH, JOURNEE, POULE, DATE, ID_EQUIPE_DOM, EQUIPE_DOM, NB_BUT_DOM,
               ID_EQUIPE_EXT, EQUIPE_EXT, NB_BUT_EXT, STATUT
        FROM `datafoot-448514.DATAFOOT.DATAFOOT_MATCH_2025`
        WHERE ID_CHAMPIONNAT = {champ_id} AND DATE <= DATE('{date_limite}')
    """
    return client.query(query).to_dataframe()

@st.cache_data(show_spinner=False)
def get_poules(champ_id):
    query = f"""
        SELECT DISTINCT POULE
        FROM `datafoot-448514.DATAFOOT.DATAFOOT_MATCH_2025`
        WHERE ID_CHAMPIONNAT = {champ_id} AND POULE IS NOT NULL
        ORDER BY POULE
    """
    return client.query(query).to_dataframe()

championnats_df = load_championnats()
penalites_df = load_penalites()

# --- Filtres utilisateur ---
st.sidebar.header("Filtres simulation")
selected_categorie = st.sidebar.selectbox("Catégorie", sorted(championnats_df["CATEGORIE"].unique()))
selected_niveau = st.sidebar.selectbox("Niveau", sorted(championnats_df[championnats_df["CATEGORIE"] == selected_categorie]["NIVEAU"].unique()))
champ_options = championnats_df[(championnats_df["CATEGORIE"] == selected_categorie) & (championnats_df["NIVEAU"] == selected_niveau)]
selected_nom = st.sidebar.selectbox("Championnat", champ_options["NOM_CHAMPIONNAT"])
champ_id = champ_options[champ_options["NOM_CHAMPIONNAT"] == selected_nom]["ID_CHAMPIONNAT"].values[0]

poules_df = get_poules(champ_id)
all_poules = sorted(poules_df["POULE"].dropna().unique())
selected_poule = st.sidebar.selectbox("Poule", ["Toutes les poules"] + all_poules) if len(all_poules) > 1 else all_poules[0]

date_limite = st.sidebar.date_input("Date de simulation", value=pd.to_datetime("2025-03-31"))
filtrer_non_joues = st.checkbox("Afficher uniquement les matchs non joués", value=True)

# --- Edition des matchs ---
st.title("🧪 Simulation What If")
matchs_complets = get_matchs(champ_id, date_limite)
if selected_poule != "Toutes les poules":
    matchs_complets = matchs_complets[matchs_complets["POULE"] == selected_poule]

matchs_simulables = matchs_complets[matchs_complets["STATUT"].isnull()] if filtrer_non_joues else matchs_complets
if matchs_simulables.empty:
    st.info("Aucun match à afficher pour cette configuration.")
    st.stop()

st.markdown("### Matchs simulables")
edited_df = st.data_editor(
    matchs_simulables[["ID_MATCH", "JOURNEE", "POULE", "DATE", "EQUIPE_DOM", "NB_BUT_DOM", "EQUIPE_EXT", "NB_BUT_EXT"]],
    num_rows="dynamic",
    use_container_width=True,
    key="simulation_scores"
)

if st.button("🔁 Recalculer le classement avec ces scores simulés"):
    # Fusion des données
    matchs_fusion = matchs_complets.copy()
    edited_scores = edited_df.set_index("ID_MATCH")[["NB_BUT_DOM", "NB_BUT_EXT"]]
    matchs_fusion.set_index("ID_MATCH", inplace=True)
    matchs_fusion.update(edited_scores)
    matchs_fusion.reset_index(inplace=True)

    # Construction des lignes pour chaque équipe
    dom = matchs_fusion[["ID_EQUIPE_DOM", "EQUIPE_DOM", "NB_BUT_DOM", "NB_BUT_EXT", "POULE"]].copy()
    dom.columns = ["ID_EQUIPE", "NOM_EQUIPE", "BUTS_POUR", "BUTS_CONTRE", "POULE"]
    dom["POINTS"] = dom.apply(
        lambda r: 3 if pd.notna(r["BUTS_POUR"]) and pd.notna(r["BUTS_CONTRE"]) and r["BUTS_POUR"] > r["BUTS_CONTRE"]
        else 1 if pd.notna(r["BUTS_POUR"]) and pd.notna(r["BUTS_CONTRE"]) and r["BUTS_POUR"] == r["BUTS_CONTRE"]
        else 0,
        axis=1
    )

    ext = matchs_fusion[["ID_EQUIPE_EXT", "EQUIPE_EXT", "NB_BUT_EXT", "NB_BUT_DOM", "POULE"]].copy()
    ext.columns = ["ID_EQUIPE", "NOM_EQUIPE", "BUTS_POUR", "BUTS_CONTRE", "POULE"]
    ext["POINTS"] = ext.apply(
        lambda r: 3 if pd.notna(r["BUTS_POUR"]) and pd.notna(r["BUTS_CONTRE"]) and r["BUTS_POUR"] > r["BUTS_CONTRE"]
        else 1 if pd.notna(r["BUTS_POUR"]) and pd.notna(r["BUTS_CONTRE"]) and r["BUTS_POUR"] == r["BUTS_CONTRE"]
        else 0,
        axis=1
    )

    classement_data = pd.concat([dom, ext], ignore_index=True)
    classement = classement_data.groupby(["ID_EQUIPE", "NOM_EQUIPE", "POULE"]).agg(
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
    ].groupby("ID_EQUIPE")["POINTS"].sum().reset_index().rename(columns={"POINTS": "PENALITES"})

    classement = classement.merge(penalites_actives, on="ID_EQUIPE", how="left")
    classement["PENALITES"] = classement["PENALITES"].fillna(0).astype(int)
    classement["POINTS"] = classement["PTS"] - classement["PENALITES"]

    # Tri final
    classement = classement.sort_values(by=["POULE", "POINTS", "DIFF", "BP"], ascending=[True, False, False, False])
    classement["CLASSEMENT"] = classement.groupby("POULE").cumcount() + 1

    # Affichage
    for poule in sorted(classement["POULE"].unique()):
        st.subheader(f"Poule {poule}")
        df_affiche = classement[classement["POULE"] == poule][[
            "CLASSEMENT", "NOM_EQUIPE", "POINTS", "PENALITES", "BP", "BC", "DIFF", "MJ"
        ]].rename(columns={"BP": "BP", "BC": "BC", "MJ": "J."})
        st.dataframe(df_affiche, use_container_width=True)

    st.success("Classement recalculé avec les scores simulés et les pénalités.")
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
