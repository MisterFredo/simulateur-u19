import streamlit as st
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account

# Configuration de la page
st.set_page_config(page_title="Simulateur Datafoot", layout="wide")

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
        ORDER BY CATEGORIE, NIVEAU
    """
    return client.query(query).to_dataframe()

championnats_df = load_championnats()

# Interface utilisateur
st.sidebar.title("🔢 Filtres")
champ_select = st.sidebar.selectbox(
    "Choisissez un championnat",
    options=championnats_df["ID_CHAMPIONNAT"],
    format_func=lambda x: championnats_df[championnats_df["ID_CHAMPIONNAT"] == x]["NOM_CHAMPIONNAT"].values[0]
)
date_select = st.sidebar.date_input("Date de simulation", value=pd.to_datetime("2025-03-31"))

# Requêtes BigQuery
@st.cache_data(show_spinner=False)
def get_classement_reel(id_champ, date):
    query = f"""
        SELECT *
        FROM `datafoot-448514.DATAFOOT.VIEW_CLASSEMENT_REEL_2025`
        WHERE ID_CHAMPIONNAT = {id_champ}
          AND DATE_CALCUL <= DATE('{date}')
        ORDER BY POULE, RANG
    """
    st.code(query)
    return client.query(query).to_dataframe()

@st.cache_data(show_spinner=False)
def get_classement_simule(id_champ, date):
    query = f"""
        SELECT *
        FROM `datafoot-448514.DATAFOOT.VIEW_CLASSEMENT_DYNAMIQUE`
        WHERE ID_CHAMPIONNAT = {id_champ}
          AND DATE_CALCUL <= DATE('{date}')
        ORDER BY POULE, RANG
    """
    st.code(query)
    return client.query(query).to_dataframe()

# Récupération des données
classement_reel = get_classement_reel(champ_select, date_select)
classement_simule = get_classement_simule(champ_select, date_select)

# Affichage
st.title("🌿 Classements à la date choisie")

if not classement_reel.empty:
    st.subheader("📊 Classement réel (matchs terminés uniquement)")
    st.dataframe(classement_reel, use_container_width=True)
    st.caption(f"🛅 Dimensions du classement réel : {classement_reel.shape}")
else:
    st.warning("Aucun classement réel disponible à cette date.")

if not classement_simule.empty:
    st.subheader("🎯 Classement simulé (avec tous les matchs)")
    st.dataframe(classement_simule, use_container_width=True)
    st.caption(f"🛅 Dimensions du classement simulé : {classement_simule.shape}")
else:
    st.warning("Aucun classement simulé disponible à cette date.")
