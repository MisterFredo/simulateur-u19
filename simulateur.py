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

date_limite = st.sidebar.date_input("Date de simulation", value=pd.to_datetime("2025-03-31"))

# Récupération du classement via la vue à jour
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
          SELECT
            ID_CHAMPIONNAT,
            POULE,
            ID_EQUIPE_DOM AS ID_EQUIPE,
            EQUIPE_DOM AS NOM_EQUIPE,
            NB_BUT_DOM AS BUTS_POUR,
            NB_BUT_EXT AS BUTS_CONTRE,
            CASE 
              WHEN NB_BUT_DOM > NB_BUT_EXT THEN 3
              WHEN NB_BUT_DOM = NB_BUT_EXT THEN 1
              ELSE 0
            END AS POINTS
          FROM matchs_termine

          UNION ALL

          SELECT
            ID_CHAMPIONNAT,
            POULE,
            ID_EQUIPE_EXT AS ID_EQUIPE,
            EQUIPE_EXT AS NOM_EQUIPE,
            NB_BUT_EXT AS BUTS_POUR,
            NB_BUT_DOM AS BUTS_CONTRE,
            CASE 
              WHEN NB_BUT_EXT > NB_BUT_DOM THEN 3
              WHEN NB_BUT_EXT = NB_BUT_DOM THEN 1
              ELSE 0
            END AS POINTS
          FROM matchs_termine
        ),

        classement AS (
          SELECT
            ID_CHAMPIONNAT,
            POULE,
            ID_EQUIPE,
            NOM_EQUIPE,
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

        SELECT *,
               RANK() OVER (
                 PARTITION BY ID_CHAMPIONNAT, POULE
                 ORDER BY PTS DESC, DIFF DESC, BP DESC
               ) AS CLASSEMENT
        FROM classement
        ORDER BY POULE, CLASSEMENT
    """
    return client.query(query).to_dataframe()

# 👇 Appel de la fonction avec les filtres actuels
classement_df = get_classement_dynamique(champ_id, date_limite)

# Affichage
title = "🏆 Classement - Datafoot"
st.title(title)
st.markdown(f"### {selected_nom} ({selected_categorie} - {selected_niveau}) au {date_limite.strftime('%d/%m/%Y')}")

if classement_df.empty:
    st.warning("Aucun classement disponible pour ces critères.")
else:
    for poule in sorted(classement_df["POULE"].unique()):
        st.subheader(f"Poule {poule}")
        df = classement_df[classement_df["POULE"] == poule][[
            "CLASSEMENT", "NOM_EQUIPE", "PTS", "BP", "BC", "DIFF", "MJ"
        ]].rename(columns={
            "PTS": "POINTS", "BP": "BUTS_POUR", "BC": "BUTS_CONTRE", "MJ": "MATCHS_JOUES"
        })
        st.dataframe(df, use_container_width=True)

# Bloc spécial classement 11e U19 National
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
        equipes_6a10 = classement_df[
            (classement_df["POULE"] == poule) &
            (classement_df["CLASSEMENT"].between(6, 10))
        ]["NOM_EQUIPE"].tolist()

        confrontations = matchs_u19[
            ((matchs_u19["EQUIPE_DOM"] == equipe_11e) & (matchs_u19["EQUIPE_EXT"].isin(equipes_6a10))) |
            ((matchs_u19["EQUIPE_EXT"] == equipe_11e) & (matchs_u19["EQUIPE_DOM"].isin(equipes_6a10)))
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

    df_comparatif = pd.DataFrame(comparatif_11e).sort_values("PTS_CONFRONT_6_10")
    df_comparatif["RANG"] = df_comparatif["PTS_CONFRONT_6_10"].rank(method="min")
    st.dataframe(df_comparatif, use_container_width=True)

# Bloc spécial classement des 2e - U17 National (ID 7)
if champ_id == 7 and not classement_df.empty:
    st.markdown("### 🥌 Comparatif des 2e (règle U17 National)")

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

st.caption("💡 Classement calculé à partir des matchs terminés uniquement, selon la date sélectionnée.")
