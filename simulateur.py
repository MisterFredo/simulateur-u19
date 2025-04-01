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

# Chargement des championnats pour la sélection
@st.cache_data(show_spinner=False)
def get_championnats():
    query = """
        SELECT ID_CHAMPIONNAT, NOM_CHAMPIONNAT, CATEGORIE, NIVEAU
        FROM `datafoot-448514.DATAFOOT.DATAFOOT_CHAMPIONNAT`
        ORDER BY CATEGORIE, NIVEAU, NOM_CHAMPIONNAT
    """
    return client.query(query).to_dataframe()

championnats_df = get_championnats()
champ_nom_to_id = dict(zip(
    championnats_df.apply(lambda row: f"{row['CATEGORIE']} - {row['NIVEAU']} - {row['NOM_CHAMPIONNAT']}", axis=1),
    championnats_df["ID_CHAMPIONNAT"]
))

# Sélections utilisateur
st.sidebar.title("⚙️ Paramètres de simulation")
champ_select = st.sidebar.selectbox("Choisissez un championnat", list(champ_nom_to_id.keys()))
date_limite = st.sidebar.date_input("Date de simulation", value=pd.to_datetime("2025-03-31"))
champ_id = champ_nom_to_id[champ_select]

# Récupération du classement réel
@st.cache_data(show_spinner=False)
def get_classement_reel(champ_id, date):
    query = f"""
        SELECT *
        FROM `datafoot-448514.DATAFOOT.VIEW_CLASSEMENT_REEL_2025`
        WHERE ID_CHAMPIONNAT = {champ_id}
          AND DATE_CALCUL <= DATE('{date}')
        ORDER BY POULE, RANG
    """
    st.code(query)
    df = client.query(query).to_dataframe()
    st.write("📦 Dimensions du classement réel :", df.shape)
    st.dataframe(df.head())
    return df

# Récupération du classement simulé
@st.cache_data(show_spinner=False)
def get_classement_simule(champ_id, date):
    query = f"""
        SELECT *
        FROM `datafoot-448514.DATAFOOT.VIEW_CLASSEMENT_DYNAMIQUE`
        WHERE ID_CHAMPIONNAT = {champ_id}
          AND DATE_CALCUL <= DATE('{date}')
        ORDER BY POULE, RANG
    """
    st.code(query)
    df = client.query(query).to_dataframe()
    st.write("📦 Dimensions du classement simulé :", df.shape)
    st.dataframe(df.head())
    return df

# Récupération des données
st.title("📊 Comparaison des classements - Datafoot")
classement_reel = get_classement_reel(champ_id, date_limite)
classement_simule = get_classement_simule(champ_id, date_limite)

if not classement_reel.empty and not classement_simule.empty:
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
else:
    st.warning("Aucun classement disponible pour la date et le championnat sélectionnés.")

st.caption("💡 Comparaison entre le classement à date (matchs terminés uniquement) et la projection avec tous les matchs (simulé).")
