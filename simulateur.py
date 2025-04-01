import streamlit as st
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account

# Configuration de la page
st.set_page_config(page_title="Classement RÉEL - Datafoot", layout="wide")

# Connexion à BigQuery via secrets
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"]
)
client = bigquery.Client(credentials=credentials, project=credentials.project_id)

# Récupération des données championnat (catégorie, niveau, etc.)
@st.cache_data(show_spinner=False)
def load_championnats():
    query = """
        SELECT ID_CHAMPIONNAT, NOM_CHAMPIONNAT, CATEGORIE, NIVEAU
        FROM `datafoot-448514.DATAFOOT.DATAFOOT_CHAMPIONNAT`
        ORDER BY CATEGORIE, NIVEAU, NOM_CHAMPIONNAT
    """
    return client.query(query).to_dataframe()

championnats_df = load_championnats()

# Filtres
st.sidebar.header("Filtres")
selected_categorie = st.sidebar.selectbox("Catégorie", sorted(championnats_df["CATEGORIE"].unique()))
selected_niveau = st.sidebar.selectbox("Niveau", sorted(championnats_df[championnats_df["CATEGORIE"] == selected_categorie]["NIVEAU"].unique()))
champ_options = championnats_df[
    (championnats_df["CATEGORIE"] == selected_categorie) &
    (championnats_df["NIVEAU"] == selected_niveau)
]
selected_nom = st.sidebar.selectbox("Championnat", champ_options["NOM_CHAMPIONNAT"])

champ_id = champ_options[champ_options["NOM_CHAMPIONNAT"] == selected_nom]["ID_CHAMPIONNAT"].values[0]

# Date de simulation
date_limite = st.sidebar.date_input("Date de simulation", value=pd.to_datetime("2025-03-31"))

# Récupération du classement réel
@st.cache_data(show_spinner=False)
def get_classement_reel(id_championnat, date):
    query = f"""
        SELECT *
        FROM `datafoot-448514.DATAFOOT.VIEW_CLASSEMENT_REEL_2025`
        WHERE ID_CHAMPIONNAT = {id_championnat}
          AND DATE_CALCUL <= DATE('{date}')
        ORDER BY POULE, RANG
    """
    return client.query(query).to_dataframe()

classement_reel = get_classement_reel(champ_id, date_limite)

st.title("🏆 Classement RÉEL - Datafoot")
st.markdown(f"### {selected_nom} ({selected_categorie} - {selected_niveau}) au {date_limite.strftime('%d/%m/%Y')}")

if classement_reel.empty:
    st.warning("Aucun classement disponible pour ces critères.")
else:
    poules = classement_reel["POULE"].unique()
    for poule in sorted(poules):
        st.subheader(f"Poule {poule}")
        st.dataframe(
            classement_reel[classement_reel["POULE"] == poule][[
                "RANG", "NOM_EQUIPE", "POINTS", "MATCHS_JOUES", "BUTS_POUR", "BUTS_CONTRE", "DIFF"
            ]],
            use_container_width=True
        )

st.caption("💡 Classement calculé à partir des matchs terminés uniquement, à la date choisie.")
