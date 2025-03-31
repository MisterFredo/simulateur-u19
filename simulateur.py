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
date_limite = st.date_input("Date de simulation", value=pd.to_datetime("2025-03-31"))

# Requête dynamique : classement réel
@st.cache_data(show_spinner=False)
def get_classement_reel(date):
    query = f"""
        SELECT *
        FROM `datafoot-448514.DATAFOOT.VIEW_CLASSEMENT_REEL`
        WHERE DATE_CALCUL = DATE('{date}')
        ORDER BY ID_CHAMPIONNAT, POULE, RANG
    """
    return client.query(query).to_dataframe()

# Requête dynamique : classement simulé
@st.cache_data(show_spinner=False)
def get_classement_simule(date):
    query = f"""
        SELECT *
        FROM `datafoot-448514.DATAFOOT.VIEW_CLASSEMENT_DYNAMIQUE`
        WHERE DATE_CALCUL = DATE('{date}')
        ORDER BY ID_CHAMPIONNAT, POULE, RANG
    """
    return client.query(query).to_dataframe()

# Récupération des classements
classement_reel = get_classement_reel(date_limite)
classement_simule = get_classement_simule(date_limite)

# Comparaison des deux classements
st.header("📊 Comparaison des classements à la date choisie")

championnats = classement_reel["ID_CHAMPIONNAT"].unique()
for champ in championnats:
    sous_reel = classement_reel[classement_reel["ID_CHAMPIONNAT"] == champ]
    sous_sim = classement_simule[classement_simule["ID_CHAMPIONNAT"] == champ]
    poules = sous_reel["POULE"].unique()

    for poule in poules:
        st.subheader(f"Championnat {champ} - Poule {poule}")

        df_reel = sous_reel[sous_reel["POULE"] == poule][["RANG", "NOM_EQUIPE", "POINTS"]].rename(columns={
            "RANG": "RANG_RÉEL", "NOM_EQUIPE": "ÉQUIPE_RÉEL", "POINTS": "POINTS_RÉEL"
        })

        df_sim = sous_sim[sous_sim["POULE"] == poule][["RANG", "NOM_EQUIPE", "POINTS"]].rename(columns={
            "RANG": "RANG_SIMULÉ", "NOM_EQUIPE": "ÉQUIPE_SIMULÉ", "POINTS": "POINTS_SIMULÉ"
        })

        df_comparaison = pd.concat([df_reel.reset_index(drop=True), df_sim.reset_index(drop=True)], axis=1)
        st.dataframe(df_comparaison, use_container_width=True)

st.caption("💡 Comparaison entre le classement à date (matchs terminés uniquement) et la projection avec tous les matchs (simulé).")
