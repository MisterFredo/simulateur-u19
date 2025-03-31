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

# Choix des dates
st.title("⚽ Simulateur de classement - Datafoot")
col1, col2 = st.columns(2)
with col1:
    date_debut = st.date_input("Date de début", value=pd.to_datetime("2024-08-01"))
with col2:
    date_fin = st.date_input("Date de fin (simulation)", value=pd.to_datetime("2025-03-31"))

# Requête dynamique : classement réel (matchs terminés)
@st.cache_data(show_spinner=False)
def get_classement_reel(date_debut, date_fin):
    query = f"""
        SELECT *
        FROM `datafoot-448514.DATAFOOT.VIEW_CLASSEMENT_REEL_2025`
        WHERE DATE_MATCH BETWEEN DATE('{date_debut}') AND DATE('{date_fin}')
        ORDER BY ID_CHAMPIONNAT, POULE, RANG
    """
    return client.query(query).to_dataframe()

# Requête dynamique : classement simulé (tous les matchs)
@st.cache_data(show_spinner=False)
def get_classement_simule(date_debut, date_fin):
    query = f"""
        SELECT *
        FROM `datafoot-448514.DATAFOOT.VIEW_CLASSEMENT_DYNAMIQUE`
        WHERE DATE_MATCH BETWEEN DATE('{date_debut}') AND DATE('{date_fin}')
        ORDER BY ID_CHAMPIONNAT, POULE, RANG
    """
    return client.query(query).to_dataframe()

# Récupération des classements
classement_reel = get_classement_reel(date_debut, date_fin)
classement_simule = get_classement_simule(date_debut, date_fin)

# Comparaison des deux classements
st.header("📊 Comparaison des classements entre deux dates")

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

st.caption("💡 Classement réel = uniquement les matchs terminés. Classement simulé = tous les matchs entre les deux dates.")
