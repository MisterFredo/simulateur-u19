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

# Chargement des championnats
@st.cache_data(show_spinner=False)
def get_championnats():
    query = """
        SELECT ID_CHAMPIONNAT, NOM_CHAMPIONNAT, CATEGORIE, NIVEAU
        FROM `datafoot-448514.DATAFOOT.DATAFOOT_CHAMPIONNAT`
        ORDER BY CATEGORIE, NIVEAU, NOM_CHAMPIONNAT
    """
    return client.query(query).to_dataframe()

championnats_df = get_championnats()
championnat_nom = st.selectbox("Choisissez un championnat", options=championnats_df["NOM_CHAMPIONNAT"])
id_championnat = int(championnats_df[championnats_df["NOM_CHAMPIONNAT"] == championnat_nom]["ID_CHAMPIONNAT"].values[0])

# Choix de la date
st.title("⚽ Simulateur de classement - Datafoot")
date_limite = st.date_input("Date de simulation", value=pd.to_datetime("2025-03-31"))

# Requête : classement réel
@st.cache_data(show_spinner=False)
def get_classement_reel(date, id_championnat):
    query = f"""
        SELECT *
        FROM `datafoot-448514.DATAFOOT.VIEW_CLASSEMENT_REEL_2025`
        WHERE DATE_CALCUL = DATE('{date}') AND ID_CHAMPIONNAT = {id_championnat}
        ORDER BY POULE, RANG
    """
    return client.query(query).to_dataframe()

# Requête : classement simulé
@st.cache_data(show_spinner=False)
def get_classement_simule(date, id_championnat):
    query = f"""
        SELECT *
        FROM `datafoot-448514.DATAFOOT.VIEW_CLASSEMENT_DYNAMIQUE`
        WHERE DATE_CALCUL = DATE('{date}') AND ID_CHAMPIONNAT = {id_championnat}
        ORDER BY POULE, RANG
    """
    return client.query(query).to_dataframe()

# Récupération des données
classement_reel = get_classement_reel(date_limite, id_championnat)
classement_simule = get_classement_simule(date_limite, id_championnat)

# Affichage des classements
if not classement_reel.empty and not classement_simule.empty:
    st.header("📊 Comparaison des classements à la date choisie")

    for poule in sorted(classement_reel["POULE"].unique()):
        st.subheader(f"Poule {poule}")

        df_reel = classement_reel[classement_reel["POULE"] == poule][["RANG", "NOM_EQUIPE", "POINTS"]].rename(columns={
            "RANG": "RANG_RÉEL", "NOM_EQUIPE": "ÉQUIPE_RÉEL", "POINTS": "POINTS_RÉEL"
        })

        df_sim = classement_simule[classement_simule["POULE"] == poule][["RANG", "NOM_EQUIPE", "POINTS"]].rename(columns={
            "RANG": "RANG_SIMULÉ", "NOM_EQUIPE": "ÉQUIPE_SIMULÉ", "POINTS": "POINTS_SIMULÉ"
        })

        df_comparaison = pd.concat([df_reel.reset_index(drop=True), df_sim.reset_index(drop=True)], axis=1)
        st.dataframe(df_comparaison, use_container_width=True)
else:
    st.info("Aucune donnée disponible pour ce championnat et cette date.")

st.caption("💡 Comparaison entre le classement à date (matchs terminés uniquement) et la projection avec tous les matchs (simulé).")
