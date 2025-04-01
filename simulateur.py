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
def load_championnats():
    query = """
        SELECT DISTINCT ID_CHAMPIONNAT, NOM_CHAMPIONNAT, CATEGORIE, NIVEAU
        FROM `datafoot-448514.DATAFOOT.DATAFOOT_CHAMPIONNAT`
        ORDER BY CATEGORIE, NIVEAU, NOM_CHAMPIONNAT
    """
    return client.query(query).to_dataframe()

championnats_df = load_championnats()

# Barre latérale
st.sidebar.header("🔍 Filtres de sélection")
categorie = st.sidebar.selectbox("Catégorie", sorted(championnats_df["CATEGORIE"].unique()))
niveau = st.sidebar.selectbox("Niveau", sorted(championnats_df[championnats_df["CATEGORIE"] == categorie]["NIVEAU"].unique()))
championnats_filtrés = championnats_df[(championnats_df["CATEGORIE"] == categorie) & (championnats_df["NIVEAU"] == niveau)]
champ_nom = st.sidebar.selectbox("Championnat", championnats_filtrés["NOM_CHAMPIONNAT"])
id_championnat = championnats_filtrés[championnats_filtrés["NOM_CHAMPIONNAT"] == champ_nom]["ID_CHAMPIONNAT"].iloc[0]

date_limite = st.sidebar.date_input("📅 Date de simulation", value=pd.to_datetime("2025-03-31"))

# Titre principal
st.title(f"📊 Classements au {date_limite.strftime('%d/%m/%Y')} pour {champ_nom}")

# Requête classement réel
@st.cache_data(show_spinner=False)
def get_classement_reel(id_champ, date):
    query = f"""
        SELECT *
        FROM `datafoot-448514.DATAFOOT.VIEW_CLASSEMENT_REEL_2025`
        WHERE ID_CHAMPIONNAT = {id_champ} AND DATE_CALCUL = DATE('{date}')
        ORDER BY POULE, RANG
    """
    return client.query(query).to_dataframe()

# Requête classement simulé
@st.cache_data(show_spinner=False)
def get_classement_simule(id_champ, date):
    query = f"""
        SELECT *
        FROM `datafoot-448514.DATAFOOT.VIEW_CLASSEMENT_DYNAMIQUE`
        WHERE ID_CHAMPIONNAT = {id_champ} AND DATE_CALCUL = DATE('{date}')
        ORDER BY POULE, RANG
    """
    return client.query(query).to_dataframe()

classement_reel = get_classement_reel(id_championnat, date_limite)
classement_simule = get_classement_simule(id_championnat, date_limite)

# Affichage comparé par poule
if not classement_reel.empty and not classement_simule.empty:
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
    st.warning("Aucune donnée disponible pour ce championnat à cette date.")

st.caption("💡 Classement réel : matchs terminés uniquement — Classement simulé : projection avec tous les matchs.")
