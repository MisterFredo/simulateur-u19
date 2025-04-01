import streamlit as st
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account

# Configuration de la page
st.set_page_config(page_title="Classement Réel - Datafoot", layout="wide")

# Connexion BigQuery
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

# Barre latérale pour sélection
st.sidebar.title("Filtrage")
champ_select = st.sidebar.selectbox(
    "Choisissez un championnat",
    options=championnats_df.index,
    format_func=lambda i: f"{championnats_df.loc[i, 'NOM_CHAMPIONNAT']} ({championnats_df.loc[i, 'CATEGORIE']} - {championnats_df.loc[i, 'NIVEAU']})"
)

champ_id = int(championnats_df.loc[champ_select, "ID_CHAMPIONNAT"])

# Date de simulation
st.sidebar.date_input("Date de simulation", value=pd.to_datetime("2025-03-31"), key="date_input")
date_limite = st.sidebar.session_state.date_input

# Requête classement réel
@st.cache_data(show_spinner=False)
def get_classement_reel(champ_id, date):
    query = f"""
        SELECT *
        FROM `datafoot-448514.DATAFOOT.VIEW_CLASSEMENT_REEL_2025`
        WHERE ID_CHAMPIONNAT = {champ_id}
          AND DATE_CALCUL <= DATE('{date}')
        ORDER BY POULE, RANG
    """
    return client.query(query).to_dataframe()

classement = get_classement_reel(champ_id, date_limite)

# Affichage du classement
st.title("Classement réel à une date donnée")
st.markdown(f"### Championnat : **{championnats_df.loc[champ_select, 'NOM_CHAMPIONNAT']}**")
st.markdown(f"Date choisie : `{date_limite}`")

if not classement.empty:
    st.dataframe(classement, use_container_width=True)
else:
    st.warning("Aucun classement disponible à cette date pour ce championnat.")
