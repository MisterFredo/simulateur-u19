import streamlit as st
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account

st.set_page_config(page_title="Simulateur Datafoot", layout="wide")

# Authentification
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"]
)
client = bigquery.Client(credentials=credentials, project=credentials.project_id)

# Sélection des filtres
st.sidebar.title("Filtres")

champ_df = client.query("SELECT * FROM `datafoot-448514.DATAFOOT.DATAFOOT_CHAMPIONNAT`").to_dataframe()
champ_df = champ_df.sort_values(["CATEGORIE", "NIVEAU", "NOM_CHAMPIONNAT"])

categorie = st.sidebar.selectbox("Catégorie", champ_df["CATEGORIE"].unique())
niveau = st.sidebar.selectbox("Niveau", champ_df[champ_df["CATEGORIE"] == categorie]["NIVEAU"].unique())
champ_nom = st.sidebar.selectbox(
    "Championnat",
    champ_df[(champ_df["CATEGORIE"] == categorie) & (champ_df["NIVEAU"] == niveau)]["NOM_CHAMPIONNAT"]
)
id_championnat = champ_df[champ_df["NOM_CHAMPIONNAT"] == champ_nom]["ID_CHAMPIONNAT"].values[0]

# Sélection de la date
date_limite = st.sidebar.date_input("Date de simulation", value=pd.to_datetime("2025-03-31"))

# Fonctions pour récupérer les classements
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
    return client.query(query).to_dataframe()

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
    return client.query(query).to_dataframe()

# Affichage des classements
st.title("📊 Simulateur de classement - Datafoot")
st.markdown(f"**Championnat sélectionné :** {champ_nom}")
st.markdown(f"**Date de simulation :** {date_limite.strftime('%d/%m/%Y')}")

reel = get_classement_reel(id_championnat, date_limite)
simule = get_classement_simule(id_championnat, date_limite)

if not reel.empty and not simule.empty:
    for poule in sorted(reel["POULE"].unique()):
        st.subheader(f"Poule {poule}")
        df_r = reel[reel["POULE"] == poule][["RANG", "NOM_EQUIPE", "POINTS"]].rename(columns={
            "RANG": "RANG_RÉEL", "NOM_EQUIPE": "ÉQUIPE_RÉEL", "POINTS": "POINTS_RÉEL"
        }).reset_index(drop=True)

        df_s = simule[simule["POULE"] == poule][["RANG", "NOM_EQUIPE", "POINTS"]].rename(columns={
            "RANG": "RANG_SIMULÉ", "NOM_EQUIPE": "ÉQUIPE_SIMULÉ", "POINTS": "POINTS_SIMULÉ"
        }).reset_index(drop=True)

        comparaison = pd.concat([df_r, df_s], axis=1)
        st.dataframe(comparaison, use_container_width=True)
else:
    st.warning("Aucun classement disponible pour ces critères.")

st.caption("💡 Classement réel : uniquement les matchs terminés. Classement simulé : projection en incluant tous les matchs.")
