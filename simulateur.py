import streamlit as st
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account

# Configuration de la page
st.set_page_config(page_title="Classement - Datafoot", layout="wide")

# Connexion à BigQuery via secrets
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

# Filtres latéraux
st.sidebar.header("Filtres")
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

# Temporaire : pour charger les poules avant d'afficher la date
@st.cache_data(show_spinner=False)
def get_poules_temp(champ_id):
    query = f"""
        SELECT DISTINCT POULE
        FROM `datafoot-448514.DATAFOOT.DATAFOOT_MATCH_2025`
        WHERE ID_CHAMPIONNAT = {champ_id}
          AND POULE IS NOT NULL
        ORDER BY POULE
    """
    return client.query(query).to_dataframe()

poules_temp = get_poules_temp(champ_id)
all_poules = sorted(poules_temp["POULE"].dropna().unique())
if len(all_poules) > 1:
    selected_poule = st.sidebar.selectbox("Poule", ["Toutes les poules"] + all_poules)
else:
    selected_poule = all_poules[0] if all_poules else "Toutes les poules"

# Date limite de simulation
date_limite = st.sidebar.date_input("Date de simulation", value=pd.to_datetime("2025-03-31"))

# Classement
@st.cache_data(show_spinner=False)
def get_classement_dynamique(champ_id, date_limite):
    query = f"""
        WITH matchs_termine AS (
          SELECT *
          FROM `datafoot-448514.DATAFOOT.DATAFOOT_MATCH_2025`
          WHERE STATUT = 'TERMINE'
            AND ID_CHAMPIONNAT = {champ_id}
            AND DATE <= DATE('{date_limite}')
        ),
        match_equipes AS (
          SELECT ID_CHAMPIONNAT, POULE, ID_EQUIPE_DOM AS ID_EQUIPE, EQUIPE_DOM AS NOM_EQUIPE,
                 NB_BUT_DOM AS BUTS_POUR, NB_BUT_EXT AS BUTS_CONTRE,
                 CASE WHEN NB_BUT_DOM > NB_BUT_EXT THEN 3 WHEN NB_BUT_DOM = NB_BUT_EXT THEN 1 ELSE 0 END AS POINTS
          FROM matchs_termine
          UNION ALL
          SELECT ID_CHAMPIONNAT, POULE, ID_EQUIPE_EXT, EQUIPE_EXT, NB_BUT_EXT, NB_BUT_DOM,
                 CASE WHEN NB_BUT_EXT > NB_BUT_DOM THEN 3 WHEN NB_BUT_EXT = NB_BUT_DOM THEN 1 ELSE 0 END
          FROM matchs_termine
        ),
        classement AS (
          SELECT ID_CHAMPIONNAT, POULE, ID_EQUIPE, NOM_EQUIPE,
                 COUNT(*) AS MJ,
                 SUM(CASE WHEN POINTS = 3 THEN 1 ELSE 0 END) AS G,
                 SUM(CASE WHEN POINTS = 1 THEN 1 ELSE 0 END) AS N,
                 SUM(CASE WHEN POINTS = 0 THEN 1 ELSE 0 END) AS P,
                 SUM(BUTS_POUR) AS BP,
                 SUM(BUTS_CONTRE) AS BC,
                 SUM(BUTS_POUR - BUTS_CONTRE) AS DIFF,
                 SUM(POINTS) AS PTS
          FROM match_equipes
          GROUP BY ID_CHAMPIONNAT, POULE, ID_EQUIPE, NOM_EQUIPE
        )
        SELECT *, RANK() OVER (PARTITION BY ID_CHAMPIONNAT, POULE ORDER BY PTS DESC, DIFF DESC, BP DESC) AS CLASSEMENT
        FROM classement
        ORDER BY POULE, CLASSEMENT
    """
    return client.query(query).to_dataframe()

# Chargement du classement complet (non filtré)
classement_complet = get_classement_dynamique(champ_id, date_limite)

# 🔁 Intégration des pénalités
@st.cache_data(show_spinner=False)
def load_penalites():
    query = """
        SELECT ID_EQUIPE, ID_CHAMPIONNAT, POINTS, DATE
        FROM `datafoot-448514.DATAFOOT.DATAFOOT_PENALITE`
    """
    return client.query(query).to_dataframe()

penalites_df = load_penalites()

# Sélection des pénalités applicables
penalites_actives = penalites_df[
    (penalites_df["ID_CHAMPIONNAT"] == champ_id) &
    (penalites_df["DATE"] <= pd.to_datetime(date_limite))
]

# Agrégation par équipe
penalites_agg = penalites_actives.groupby("ID_EQUIPE")["POINTS"].sum().reset_index()
penalites_agg.rename(columns={"POINTS": "PENALITES"}, inplace=True)

# Jointure avec le classement
classement_df = classement_complet.merge(penalites_agg, on="ID_EQUIPE", how="left")
classement_df["PENALITES"] = classement_df["PENALITES"].fillna(0).astype(int)

# Mise à jour des points après pénalités
classement_df["POINTS"] = classement_df["PTS"] - classement_df["PENALITES"]

# Recalcul du classement
classement_df = classement_df.sort_values(by=["POULE", "POINTS", "DIFF", "BP"], ascending=[True, False, False, False])
classement_df["CLASSEMENT"] = classement_df.groupby("POULE").cumcount() + 1

# Filtrage si une poule spécifique est sélectionnée
if selected_poule != "Toutes les poules":
    classement_df = classement_df[classement_df["POULE"] == selected_poule]

# Affichage principal
st.title("\U0001F3C6 Classement - Datafoot")
st.markdown(f"### {selected_nom} ({selected_categorie} - {selected_niveau}) au {date_limite.strftime('%d/%m/%Y')}")

if classement_df.empty:
    st.warning("Aucun classement disponible pour ces critères.")
else:
    for poule in sorted(classement_df["POULE"].unique()):
        st.subheader(f"Poule {poule}")
        df = classement_df[classement_df["POULE"] == poule][[
            "CLASSEMENT", "NOM_EQUIPE", "PTS", "PENALITES", "BP", "BC", "DIFF", "MJ"
        ]].rename(columns={
            "BP": "BP",
            "BC": "BC",
            "MJ": "J."
        })
        st.dataframe(df, use_container_width=True)

st.caption("💡 Classement calculé à partir des matchs terminés uniquement, selon la date sélectionnée. Les pénalités sont déduites des points.")


if classement_df.empty:
    st.warning("Aucun classement disponible pour ces critères.")
else:
    for poule in sorted(classement_df["POULE"].unique()):
        st.subheader(f"Poule {poule}")
        df = classement_df[classement_df["POULE"] == poule][[
            "CLASSEMENT", "NOM_EQUIPE", "PTS", "PENALITES", "BP", "BC", "DIFF", "MJ"
        ]].rename(columns={
            "BP": "BP",
            "BC": "BC",
            "MJ": "J."
        })
        st.dataframe(df, use_container_width=True)

# Les règles spécifiques sont désormais à adapter avec "classement_complet" pour avoir toutes les poules disponibles


# Cas particuliers (U19 / U17 / N2)
if selected_poule == "Toutes les poules":

    # U19 National - 11e
    if champ_id == 6 and not classement_df.empty:
        st.markdown("### 🚨 Classement spécial des 11èmes (règle U19 National)")
        df_11e = classement_df[classement_df["CLASSEMENT"] == 11]
        comparatif_11e = []

        @st.cache_data(show_spinner=False)
        def get_matchs_u19(champ_id, date_limite):
            query = f"""
                SELECT *
                FROM `datafoot-448514.DATAFOOT.DATAFOOT_MATCH_2025`
                WHERE STATUT = 'TERMINE'
                  AND ID_CHAMPIONNAT = {champ_id}
                  AND DATE <= DATE('{date_limite}')
            """
            return client.query(query).to_dataframe()

        matchs_u19 = get_matchs_u19(champ_id, date_limite)

        for _, row in df_11e.iterrows():
            poule = row["POULE"]
            equipe_11e = row["NOM_EQUIPE"]
            adversaires = classement_df[
                (classement_df["POULE"] == poule) &
                (classement_df["CLASSEMENT"].between(6, 10))
            ]["NOM_EQUIPE"].tolist()

            confrontations = matchs_u19[
                ((matchs_u19["EQUIPE_DOM"] == equipe_11e) & (matchs_u19["EQUIPE_EXT"].isin(adversaires))) |
                ((matchs_u19["EQUIPE_EXT"] == equipe_11e) & (matchs_u19["EQUIPE_DOM"].isin(adversaires)))
            ]

            pts = 0
            for _, m in confrontations.iterrows():
                if m["EQUIPE_DOM"] == equipe_11e:
                    if m["NB_BUT_DOM"] > m["NB_BUT_EXT"]: pts += 3
                    elif m["NB_BUT_DOM"] == m["NB_BUT_EXT"]: pts += 1
                elif m["EQUIPE_EXT"] == equipe_11e:
                    if m["NB_BUT_EXT"] > m["NB_BUT_DOM"]: pts += 3
                    elif m["NB_BUT_EXT"] == m["NB_BUT_DOM"]: pts += 1

            comparatif_11e.append({"POULE": poule, "EQUIPE": equipe_11e, "PTS_CONFRONT_6_10": pts})

        df_11e_comp = pd.DataFrame(comparatif_11e).sort_values("PTS_CONFRONT_6_10")
        df_11e_comp["RANG"] = df_11e_comp["PTS_CONFRONT_6_10"].rank(method="min")
        st.dataframe(df_11e_comp, use_container_width=True)

    # U17 National - 2e
    if champ_id == 7 and not classement_df.empty:
        st.markdown("### 🥈 Comparatif des 2e (règle U17 National)")

        df_2e = classement_df[classement_df["CLASSEMENT"] == 2]
        comparatif_2e = []

        for _, row in df_2e.iterrows():
            poule = row["POULE"]
            equipe_2e = row["NOM_EQUIPE"]

            top_5 = classement_df[
                (classement_df["POULE"] == poule) &
                (classement_df["CLASSEMENT"].between(1, 5))
            ]["NOM_EQUIPE"].tolist()

            @st.cache_data(show_spinner=False)
            def get_matchs_poule(champ_id, poule):
                query = f"""
                    SELECT EQUIPE_DOM, EQUIPE_EXT, NB_BUT_DOM, NB_BUT_EXT
                    FROM `datafoot-448514.DATAFOOT.DATAFOOT_MATCH_2025`
                    WHERE ID_CHAMPIONNAT = {champ_id}
                      AND POULE = '{poule}'
                      AND STATUT = 'TERMINE'
                """
                return client.query(query).to_dataframe()

            matchs_poule = get_matchs_poule(champ_id, poule)

            confrontations = matchs_poule[
                ((matchs_poule["EQUIPE_DOM"] == equipe_2e) & (matchs_poule["EQUIPE_EXT"].isin(top_5))) |
                ((matchs_poule["EQUIPE_EXT"] == equipe_2e) & (matchs_poule["EQUIPE_DOM"].isin(top_5)))
            ]

            pts = 0
            for _, m in confrontations.iterrows():
                if m["EQUIPE_DOM"] == equipe_2e:
                    if m["NB_BUT_DOM"] > m["NB_BUT_EXT"]: pts += 3
                    elif m["NB_BUT_DOM"] == m["NB_BUT_EXT"]: pts += 1
                elif m["EQUIPE_EXT"] == equipe_2e:
                    if m["NB_BUT_EXT"] > m["NB_BUT_DOM"]: pts += 3
                    elif m["NB_BUT_EXT"] == m["NB_BUT_DOM"]: pts += 1

            comparatif_2e.append({
                "POULE": poule,
                "EQUIPE": equipe_2e,
                "PTS_CONFRONT_TOP5": pts
            })

        df_2e_comp = pd.DataFrame(comparatif_2e).sort_values("PTS_CONFRONT_TOP5", ascending=False)
        df_2e_comp["RANG"] = df_2e_comp["PTS_CONFRONT_TOP5"].rank(method="min", ascending=False)
        st.dataframe(df_2e_comp, use_container_width=True)

    # N2 - 13e
    if champ_id == 4 and not classement_df.empty:
        st.markdown("### 🚨 Comparatif des 13e (règle N2)")

        df_13e = classement_df[classement_df["CLASSEMENT"] == 13]
        comparatif_13e = []

        @st.cache_data(show_spinner=False)
        def get_matchs_n2(champ_id, date_limite):
            query = f"""
                SELECT *
                FROM `datafoot-448514.DATAFOOT.DATAFOOT_MATCH_2025`
                WHERE STATUT = 'TERMINE'
                  AND ID_CHAMPIONNAT = {champ_id}
                  AND DATE <= DATE('{date_limite}')
            """
            return client.query(query).to_dataframe()

        matchs_n2 = get_matchs_n2(champ_id, date_limite)

        for _, row in df_13e.iterrows():
            poule = row["POULE"]
            equipe_13e = row["NOM_EQUIPE"]

            adversaires = classement_df[
                (classement_df["POULE"] == poule) &
                (classement_df["CLASSEMENT"].between(8, 12))
            ]["NOM_EQUIPE"].tolist()

            confrontations = matchs_n2[
                ((matchs_n2["EQUIPE_DOM"] == equipe_13e) & (matchs_n2["EQUIPE_EXT"].isin(adversaires))) |
                ((matchs_n2["EQUIPE_EXT"] == equipe_13e) & (matchs_n2["EQUIPE_DOM"].isin(adversaires)))
            ]

            pts = 0
            for _, m in confrontations.iterrows():
                if m["EQUIPE_DOM"] == equipe_13e:
                    if m["NB_BUT_DOM"] > m["NB_BUT_EXT"]: pts += 3
                    elif m["NB_BUT_DOM"] == m["NB_BUT_EXT"]: pts += 1
                elif m["EQUIPE_EXT"] == equipe_13e:
                    if m["NB_BUT_EXT"] > m["NB_BUT_DOM"]: pts += 3
                    elif m["NB_BUT_EXT"] == m["NB_BUT_DOM"]: pts += 1

            comparatif_13e.append({
                "POULE": poule,
                "EQUIPE": equipe_13e,
                "PTS_CONFRONT_8_12": pts
            })

        df_13e_comp = pd.DataFrame(comparatif_13e).sort_values("PTS_CONFRONT_8_12", ascending=False)
        df_13e_comp["RANG"] = df_13e_comp["PTS_CONFRONT_8_12"].rank(method="min", ascending=False)
        st.dataframe(df_13e_comp, use_container_width=True)
    # N3 - 10e
    if champ_id == 5 and not classement_df.empty:
        st.markdown("### ⚠️ Comparatif des 10e (règle N3)")

        df_10e = classement_df[classement_df["CLASSEMENT"] == 10]
        comparatif_10e = []

        @st.cache_data(show_spinner=False)
        def get_matchs_n3(champ_id, date_limite):
            query = f"""
                SELECT *
                FROM `datafoot-448514.DATAFOOT.DATAFOOT_MATCH_2025`
                WHERE STATUT = 'TERMINE'
                  AND ID_CHAMPIONNAT = {champ_id}
                  AND DATE <= DATE('{date_limite}')
            """
            return client.query(query).to_dataframe()

        matchs_n3 = get_matchs_n3(champ_id, date_limite)

        for _, row in df_10e.iterrows():
            poule = row["POULE"]
            equipe_10e = row["NOM_EQUIPE"]

            adversaires = classement_df[
                (classement_df["POULE"] == poule) &
                (classement_df["CLASSEMENT"].between(5, 9))
            ]["NOM_EQUIPE"].tolist()

            confrontations = matchs_n3[
                ((matchs_n3["EQUIPE_DOM"] == equipe_10e) & (matchs_n3["EQUIPE_EXT"].isin(adversaires))) |
                ((matchs_n3["EQUIPE_EXT"] == equipe_10e) & (matchs_n3["EQUIPE_DOM"].isin(adversaires)))
            ]

            pts = 0
            for _, m in confrontations.iterrows():
                if m["EQUIPE_DOM"] == equipe_10e:
                    if m["NB_BUT_DOM"] > m["NB_BUT_EXT"]: pts += 3
                    elif m["NB_BUT_DOM"] == m["NB_BUT_EXT"]: pts += 1
                elif m["EQUIPE_EXT"] == equipe_10e:
                    if m["NB_BUT_EXT"] > m["NB_BUT_DOM"]: pts += 3
                    elif m["NB_BUT_EXT"] == m["NB_BUT_DOM"]: pts += 1

            comparatif_10e.append({
                "POULE": poule,
                "EQUIPE": equipe_10e,
                "PTS_CONFRONT_5_9": pts
            })

        df_10e_comp = pd.DataFrame(comparatif_10e).sort_values("PTS_CONFRONT_5_9", ascending=False)
        df_10e_comp["RANG"] = df_10e_comp["PTS_CONFRONT_5_9"].rank(method="min", ascending=False)
        st.dataframe(df_10e_comp, use_container_width=True)



else:
    if champ_id in [4, 5, 6, 7]:
        st.info("🔒 Les règles spécifiques (U19, U17, N2, N3) ne sont disponibles que si toutes les poules sont affichées.")
