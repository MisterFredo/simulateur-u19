import streamlit as st
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account

# Configuration de la page
st.set_page_config(page_title="Simulateur Datafoot", layout="wide")

# Connexion BigQuery via secrets
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"]
)
client = bigquery.Client(credentials=credentials, project=credentials.project_id)

# Chargement des championnats pour les filtres
@st.cache_data(show_spinner=False)
def load_championnats():
    query = """
        SELECT DISTINCT ID_CHAMPIONNAT, NOM_CHAMPIONNAT, CATEGORIE, NIVEAU
        FROM `datafoot-448514.DATAFOOT.DATAFOOT_CHAMPIONNAT`
        ORDER BY CATEGORIE, NIVEAU, NOM_CHAMPIONNAT
    """
    return client.query(query).to_dataframe()

champ_df = load_championnats()

# Barre latérale pour filtres
st.sidebar.header("🔍 Filtres")
categorie = st.sidebar.selectbox("Catégorie", champ_df["CATEGORIE"].unique())
filtre_cat = champ_df[champ_df["CATEGORIE"] == categorie]
niveau = st.sidebar.selectbox("Niveau", filtre_cat["NIVEAU"].unique())
filtre_niv = filtre_cat[filtre_cat["NIVEAU"] == niveau]
championnat_nom = st.sidebar.selectbox("Championnat", filtre_niv["NOM_CHAMPIONNAT"].unique())
championnat_id = int(filtre_niv[filtre_niv["NOM_CHAMPIONNAT"] == championnat_nom]["ID_CHAMPIONNAT"].values[0])

date_limite = st.sidebar.date_input("Date de simulation", value=pd.to_datetime("2025-03-31"))

# Requêtes BQ
@st.cache_data(show_spinner=False)
def get_classement_reel(id_championnat, date):
    query = f"""
        SELECT *
        FROM `datafoot-448514.DATAFOOT.VIEW_CLASSEMENT_REEL_2025`
        WHERE ID_CHAMPIONNAT = {id_championnat} AND DATE_CALCUL = DATE('{date}')
        ORDER BY POULE, RANG
    """
    return client.query(query).to_dataframe()

@st.cache_data(show_spinner=False)
def get_classement_simule(id_championnat, date):
    query = f"""
        SELECT *
        FROM `datafoot-448514.DATAFOOT.VIEW_CLASSEMENT_DYNAMIQUE`
        WHERE ID_CHAMPIONNAT = {id_championnat} AND DATE_CALCUL = DATE('{date}')
        ORDER BY POULE, RANG
    """
    return client.query(query).to_dataframe()

# Affichage
st.title("🌟 Simulateur de classement - Datafoot")
st.caption("Compare les classements réels (matchs terminés) et simulés (tous les matchs joués + non joués)")

reel_df = get_classement_reel(championnat_id, date_limite)
simule_df = get_classement_simule(championnat_id, date_limite)

if reel_df.empty or simule_df.empty:
    st.warning("Aucun classement trouvé pour ces critères.")
else:
    for poule in sorted(reel_df["POULE"].unique()):
        st.subheader(f"Poule {poule}")

        df_reel = reel_df[reel_df["POULE"] == poule][["RANG", "NOM_EQUIPE", "POINTS"]].rename(columns={
            "RANG": "RANG_RÉEL", "NOM_EQUIPE": "ÉQUIPE_RÉEL", "POINTS": "POINTS_RÉEL"
        })

        df_sim = simule_df[simule_df["POULE"] == poule][["RANG", "NOM_EQUIPE", "POINTS"]].rename(columns={
            "RANG": "RANG_SIMULÉ", "NOM_EQUIPE": "ÉQUIPE_SIMULÉ", "POINTS": "POINTS_SIMULÉ"
        })

        comparaison = pd.concat([df_reel.reset_index(drop=True), df_sim.reset_index(drop=True)], axis=1)
        st.dataframe(comparaison, use_container_width=True)
