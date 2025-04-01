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

# Récupération des métadonnées des championnats
@st.cache_data(show_spinner=False)
def get_championnats():
    query = """
        SELECT DISTINCT ID_CHAMPIONNAT, NOM_CHAMPIONNAT, CATEGORIE, NIVEAU
        FROM `datafoot-448514.DATAFOOT.DATAFOOT_CHAMPIONNAT`
        ORDER BY CATEGORIE, NIVEAU, NOM_CHAMPIONNAT
    """
    return client.query(query).to_dataframe()

champ_df = get_championnats()

# Filtres utilisateur
st.sidebar.header("Filtres")
categorie_choisie = st.sidebar.selectbox("Catégorie", champ_df["CATEGORIE"].unique())
champ_filtre = champ_df[champ_df["CATEGORIE"] == categorie_choisie]
niveau_choisi = st.sidebar.selectbox("Niveau", champ_filtre["NIVEAU"].unique())
champ_filtre = champ_filtre[champ_filtre["NIVEAU"] == niveau_choisi]
championnat_nom = st.sidebar.selectbox("Championnat", champ_filtre["NOM_CHAMPIONNAT"].unique())

# Récupération de l'ID_CHAMPIONNAT correspondant
championnat_id = champ_filtre[champ_filtre["NOM_CHAMPIONNAT"] == championnat_nom]["ID_CHAMPIONNAT"].values[0]

# Choix de la date
st.title("⚽ Simulateur de classement - Datafoot")
date_limite = st.date_input("Date de simulation", value=pd.to_datetime("2025-03-31"))

# Requête dynamique : classement réel
@st.cache_data(show_spinner=False)
def get_classement_reel(date, id_champ):
    query = f"""
        SELECT *
        FROM `datafoot-448514.DATAFOOT.VIEW_CLASSEMENT_REEL_2025`
        WHERE DATE_CALCUL = DATE('{date}') AND ID_CHAMPIONNAT = '{id_champ}'
        ORDER BY POULE, RANG
    """
    return client.query(query).to_dataframe()

# Requête dynamique : classement simulé
@st.cache_data(show_spinner=False)
def get_classement_simule(date, id_champ):
    query = f"""
        SELECT *
        FROM `datafoot-448514.DATAFOOT.VIEW_CLASSEMENT_DYNAMIQUE`
        WHERE DATE_CALCUL = DATE('{date}') AND ID_CHAMPIONNAT = '{id_champ}'
        ORDER BY POULE, RANG
    """
    return client.query(query).to_dataframe()

# Récupération des classements
classement_reel = get_classement_reel(date_limite, championnat_id)
classement_simule = get_classement_simule(date_limite, championnat_id)

# Comparaison des deux classements
st.header(f"📊 Classement du championnat {championnat_nom} à la date du {date_limite.strftime('%d/%m/%Y')}")
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

st.caption("💡 Comparaison entre le classement à date (matchs terminés uniquement) et la projection avec tous les matchs (simulé).")
