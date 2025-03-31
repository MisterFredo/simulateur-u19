import streamlit as st
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account

# Configuration de la page
st.set_page_config(page_title="Simulateur Datafoot", layout="wide")

# Connexion à BigQuery via secrets
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"]
)
client = bigquery.Client(credentials=credentials, project=credentials.project_id)

# Choix de la date
st.title("⚽ Simulateur de classement - Datafoot")
date_limite = st.date_input("Date limite des matchs pris en compte", value=pd.to_datetime("2025-03-31"))

# Classement réel : uniquement les matchs terminés
@st.cache_data(show_spinner=False)
def get_classement_reel(date):
    query = f"""
        SELECT *
        FROM `datafoot-448514.DATAFOOT.VIEW_CLASSEMENT_REEL_2025`
        WHERE DATE <= DATE('{date}')
        ORDER BY ID_CHAMPIONNAT, POULE, RANG
    """
    return client.query(query).to_dataframe()

# Classement dynamique : tous les matchs datés
@st.cache_data(show_spinner=False)
def get_classement_dynamique(date):
    query = f"""
        SELECT *
        FROM `datafoot-448514.DATAFOOT.VIEW_CLASSEMENT_DYNAMIQUE`
        WHERE DATE <= DATE('{date}')
        ORDER BY ID_CHAMPIONNAT, POULE, RANG
    """
    return client.query(query).to_dataframe()

# Chargement des classements
classement_reel = get_classement_reel(date_limite)
classement_dynamique = get_classement_dynamique(date_limite)

# Comparaison
st.header("📊 Comparaison des classements à la date choisie")

for champ in classement_reel["ID_CHAMPIONNAT"].unique():
    sous_reel = classement_reel[classement_reel["ID_CHAMPIONNAT"] == champ]
    sous_dyn = classement_dynamique[classement_dynamique["ID_CHAMPIONNAT"] == champ]

    for poule in sous_reel["POULE"].unique():
        st.subheader(f"Championnat {champ} - Poule {poule}")

        df_reel = sous_reel[sous_reel["POULE"] == poule][["RANG", "NOM_EQUIPE", "POINTS"]].rename(columns={
            "RANG": "RANG_RÉEL", "NOM_EQUIPE": "ÉQUIPE_RÉEL", "POINTS": "POINTS_RÉEL"
        })

        df_dyn = sous_dyn[sous_dyn["POULE"] == poule][["RANG", "NOM_EQUIPE", "POINTS"]].rename(columns={
            "RANG": "RANG_DYNAMIQUE", "NOM_EQUIPE": "ÉQUIPE_DYNAMIQUE", "POINTS": "POINTS_DYNAMIQUE"
        })

        df_comparaison = pd.concat([df_reel.reset_index(drop=True), df_dyn.reset_index(drop=True)], axis=1)
        st.dataframe(df_comparaison, use_container_width=True)

st.caption("📝 Classement réel = uniquement les matchs terminés. Classement dynamique = tous les matchs avec une date.")
