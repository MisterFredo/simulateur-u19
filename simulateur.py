import streamlit as st
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account
import json

st.set_page_config(page_title="Simulateur U19 Datafoot", layout="wide")

# Connexion à BigQuery via secrets Streamlit
service_account_info = json.loads(st.secrets["gcp_service_account"])
credentials = service_account.Credentials.from_service_account_info(service_account_info)
client = bigquery.Client(credentials=credentials, project=credentials.project_id)

st.title("🌟 Simulateur relégation U19 - Datafoot")

# Choix de la date de simulation
date_limite = st.date_input("Choisissez la date de calcul des classements", value=pd.to_datetime("2025-03-31"))

# Récupération des classements dynamiques
@st.cache_data(show_spinner=False)
def get_classements(date):
    query = f"""
    SELECT *
    FROM `datafoot-448514.DATAFOOT.VIEW_CLASSEMENT_DYNAMIQUE_U19_2025`
    ORDER BY POULE, RANG
    """
    return client.query(query).to_dataframe()

classement_df = get_classements(date_limite)
st.subheader("Classements dynamiques par poule")
for poule in sorted(classement_df["POULE"].unique()):
    st.markdown(f"### Poule {poule}")
    st.dataframe(classement_df[classement_df["POULE"] == poule][["RANG", "NOM_EQUIPE", "POINTS"]].reset_index(drop=True), use_container_width=True)

# Classement des 11e contre 6-10 (à date)
@st.cache_data(show_spinner=False)
def get_11e_classement():
    query = """
    SELECT *
    FROM `datafoot-448514.DATAFOOT.VIEW_CLASSEMENT_11E_SPECIFIQUE_U19_2025`
    ORDER BY POINTS_OBTENUS ASC, MOYENNE_POINTS_PAR_MATCH ASC
    """
    return client.query(query).to_dataframe()

st.subheader("Classement spécifique des 11e à date")
st.dataframe(get_11e_classement(), use_container_width=True)

# Classement des 11e après simulation
@st.cache_data(show_spinner=False)
def get_11e_simule():
    query = """
    SELECT *
    FROM `datafoot-448514.DATAFOOT.VIEW_CLASSEMENT_11E_SIMULE_U19_2025`
    ORDER BY POINTS_OBTENUS ASC, MOYENNE_POINTS_PAR_MATCH ASC
    """
    return client.query(query).to_dataframe()

st.subheader("Classement spécifique des 11e après simulation")
st.dataframe(get_11e_simule(), use_container_width=True)

st.caption("Made with ❤️ by Datafoot")
