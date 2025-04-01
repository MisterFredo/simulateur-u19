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

# Chargement des métadonnées des championnats
@st.cache_data(show_spinner=False)
def load_championnats():
    query = """
        SELECT DISTINCT ID_CHAMPIONNAT, NOM_CHAMPIONNAT, CATEGORIE, NIVEAU
        FROM `datafoot-448514.DATAFOOT.DATAFOOT_CHAMPIONNAT`
        ORDER BY CATEGORIE, NIVEAU, NOM_CHAMPIONNAT
    """
    return client.query(query).to_dataframe()

championnats_df = load_championnats()

# Interface utilisateur : sélection du championnat et de la date
titre_col, date_col = st.columns([2, 1])

with titre_col:
    selected_nom = st.selectbox("Sélectionnez un championnat", championnats_df["NOM_CHAMPIONNAT"])
    selected_row = championnats_df[championnats_df["NOM_CHAMPIONNAT"] == selected_nom].iloc[0]
    id_championnat = selected_row["ID_CHAMPIONNAT"]

with date_col:
    date_limite = st.date_input("Date de simulation", value=pd.to_datetime("2025-03-31"))

# Requêtes pour les classements
@st.cache_data(show_spinner=False)
def get_classement_reel(id_championnat, date):
    query = f"""
        SELECT *
        FROM `datafoot-448514.DATAFOOT.VIEW_CLASSEMENT_REEL_2025`
        WHERE ID_CHAMPIONNAT = {id_championnat}
          AND DATE_CALCUL = DATE('{date}')
        ORDER BY POULE, RANG
    """
    return client.query(query).to_dataframe()

@st.cache_data(show_spinner=False)
def get_classement_simule(id_championnat, date):
    query = f"""
        SELECT *
        FROM `datafoot-448514.DATAFOOT.VIEW_CLASSEMENT_DYNAMIQUE`
        WHERE ID_CHAMPIONNAT = {id_championnat}
          AND DATE_CALCUL = DATE('{date}')
        ORDER BY POULE, RANG
    """
    return client.query(query).to_dataframe()

# Affichage
st.title("⚽ Simulateur de classement - Datafoot")

classement_reel = get_classement_reel(id_championnat, date_limite)
classement_simule = get_classement_simule(id_championnat, date_limite)

if classement_reel.empty or classement_simule.empty:
    st.warning("Aucun résultat pour cette combinaison championnat/date.")
else:
    st.header("📊 Comparaison des classements à la date choisie")
    poules = classement_reel["POULE"].unique()

    for poule in poules:
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
