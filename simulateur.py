import streamlit as st
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account

# Configuration de la page
st.set_page_config(page_title="Classement Réel - Datafoot", layout="wide")

# Connexion à BigQuery via secrets
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"]
)
client = bigquery.Client(credentials=credentials, project=credentials.project_id)

# Choix de la date
st.title("🌿 Classement réel à une date donnée")
date_limite = st.date_input("Choisissez une date", value=pd.to_datetime("2025-03-31"))

# Requête BigQuery pour classement réel
@st.cache_data(show_spinner=True)
def get_classement_reel(date):
    query = f"""
        SELECT *
        FROM `datafoot-448514.DATAFOOT.VIEW_CLASSEMENT_REEL_2025`
        WHERE DATE_CALCUL = DATE('{date}')
        ORDER BY ID_CHAMPIONNAT, POULE, RANG
    """
    return client.query(query).to_dataframe()

# Récupération des données
classement_df = get_classement_reel(date_limite)

# Affichage
if classement_df.empty:
    st.warning("Aucun classement réel trouvé à cette date.")
else:
    championnats = classement_df["ID_CHAMPIONNAT"].unique()
    for champ in championnats:
        st.subheader(f"Championnat {champ}")
        sous_df = classement_df[classement_df["ID_CHAMPIONNAT"] == champ]
        for poule in sous_df["POULE"].unique():
            st.markdown(f"### Poule {poule}")
            st.dataframe(sous_df[sous_df["POULE"] == poule], use_container_width=True)
