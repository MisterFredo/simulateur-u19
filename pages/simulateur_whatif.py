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

# Récupération des pénalités
@st.cache_data(show_spinner=False)
def load_penalites():
    query = """
        SELECT ID_EQUIPE, ID_CHAMPIONNAT, POULE, POINTS, DATE
        FROM `datafoot-448514.DATAFOOT.DATA_PENALITE`
    """
    return client.query(query).to_dataframe()

penalites_df = load_penalites()

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

# Récupération du classement
classement_df = get_classement_dynamique(champ_id, date_limite)

# Récupération des pénalités actives
penalites_actives = penalites_df[
    (penalites_df["ID_CHAMPIONNAT"] == champ_id) &
    (penalites_df["DATE"] <= pd.to_datetime(date_limite))
]

# Agrégation des points de pénalité par équipe
penalites_par_equipe = penalites_actives.groupby("ID_EQUIPE")["POINTS"].sum().reset_index()
penalites_par_equipe.rename(columns={"POINTS": "PENALITES"}, inplace=True)

# Ajout dans le classement (avant filtre sur la poule)
classement_df = classement_df.merge(penalites_par_equipe, on="ID_EQUIPE", how="left")
classement_df["PENALITES"] = classement_df["PENALITES"].fillna(0).astype(int)
classement_df["POINTS"] = classement_df["PTS"] - classement_df["PENALITES"]

# Filtrage si une seule poule est sélectionnée
if selected_poule != "Toutes les poules":
    classement_df = classement_df[classement_df["POULE"] == selected_poule]


# Ajout des pénalités
penalites_actives = penalites_df[
    (penalites_df["ID_CHAMPIONNAT"] == champ_id) &
    (penalites_df["DATE"] <= pd.to_datetime(date_limite))
]

if not penalites_actives.empty:
    penalites_par_equipe = penalites_actives.groupby("ID_EQUIPE")["POINTS"].sum().reset_index()
    classement_df = classement_df.merge(penalites_par_equipe, on="ID_EQUIPE", how="left")
    classement_df["POINTS_PENALITE"] = classement_df["POINTS"].fillna(0)
    classement_df["PTS"] = classement_df["PTS"] - classement_df["POINTS_PENALITE"]
    classement_df.drop(columns=["POINTS", "POINTS_PENALITE"], inplace=True)

if selected_poule != "Toutes les poules":
    classement_df = classement_df[classement_df["POULE"] == selected_poule]

# Affichage principal
st.title("🏆 Classement - Datafoot")
st.markdown(f"### {selected_nom} ({selected_categorie} - {selected_niveau}) au {date_limite.strftime('%d/%m/%Y')}")

# 🔄 Ajout des pénalités à déduire des points
penalites_actives = penalites_df[
    (penalites_df["ID_CHAMPIONNAT"] == champ_id) &
    (penalites_df["DATE"] <= pd.to_datetime(date_limite))
]

# Aggrégation par équipe
penalites_par_equipe = penalites_actives.groupby("ID_EQUIPE")["POINTS"].sum().reset_index()
penalites_par_equipe.rename(columns={"POINTS": "PENALITES"}, inplace=True)

# Merge dans le classement
classement_df = classement_df.merge(penalites_par_equipe, on="ID_EQUIPE", how="left")
classement_df["PENALITES"] = classement_df["PENALITES"].fillna(0)
classement_df["POINTS"] = classement_df["PTS"] - classement_df["PENALITES"]

# Filtre poule si nécessaire
if selected_poule != "Toutes les poules":
    classement_df = classement_df[classement_df["POULE"] == selected_poule]

if classement_df.empty:
    st.warning("Aucun classement disponible pour ces critères.")
else:
    for poule in sorted(classement_df["POULE"].unique()):
        st.subheader(f"Poule {poule}")
        df = classement_df[classement_df["POULE"] == poule][[
            "CLASSEMENT", "NOM_EQUIPE", "POINTS", "PENALITES", "BP", "BC", "DIFF", "MJ"
        ]].rename(columns={
            "BP": "BUTS_POUR", "BC": "BUTS_CONTRE", "MJ": "MATCHS_JOUES"
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
