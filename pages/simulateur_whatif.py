import streamlit as st
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account

# Configuration
st.set_page_config(page_title="Simulation What If", layout="wide")

# Connexion BigQuery (identique à ta page principale)
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"]
)
client = bigquery.Client(credentials=credentials, project=credentials.project_id)

# Chargement des championnats
@st.cache_data(show_spinner=False)
def load_championnats():
    query = """
        SELECT ID_CHAMPIONNAT, NOM_CHAMPIONNAT, CATEGORIE, NIVEAU
        FROM `datafoot-448514.DATAFOOT.DATAFOOT_CHAMPIONNAT`
        ORDER BY CATEGORIE, NIVEAU, NOM_CHAMPIONNAT
    """
    return client.query(query).to_dataframe()

championnats_df = load_championnats()

# Filtres
st.sidebar.header("Filtres simulation")
selected_categorie = st.sidebar.selectbox("Catégorie", sorted(championnats_df["CATEGORIE"].unique()))
selected_niveau = st.sidebar.selectbox(
    "Niveau", sorted(championnats_df[championnats_df["CATEGORIE"] == selected_categorie]["NIVEAU"].unique())
)
champ_options = championnats_df[
    (championnats_df["CATEGORIE"] == selected_categorie) &
    (championnats_df["NIVEAU"] == selected_niveau)
]
selected_nom = st.sidebar.selectbox("Championnat", champ_options["NOM_CHAMPIONNAT"])
champ_id = champ_options[champ_options["NOM_CHAMPIONNAT"] == selected_nom]["ID_CHAMPIONNAT"].values[0]
date_limite = st.sidebar.date_input("Date max à prendre en compte", value=pd.to_datetime("2025-03-31"))

# Affichage des matchs modifiables
st.title("🧪 Simulation What If")

filtrer_non_joues = st.checkbox("Afficher uniquement les matchs non joués", value=True)

@st.cache_data(show_spinner=False)
def get_matchs_modifiables(champ_id, date_limite, non_joues_only):
    condition = "AND STATUT IS NULL" if non_joues_only else ""
    query = f"""
        SELECT 
            ID_MATCH,
            JOURNEE,
            POULE,
            DATE,
            EQUIPE_DOM,
            NB_BUT_DOM,
            EQUIPE_EXT,
            NB_BUT_EXT,
            STATUT
        FROM `datafoot-448514.DATAFOOT.DATAFOOT_MATCH_2025`
        WHERE ID_CHAMPIONNAT = {champ_id}
          AND DATE <= DATE('{date_limite}')
          {condition}
        ORDER BY DATE, JOURNEE
    """
    return client.query(query).to_dataframe()

matchs_simulables = get_matchs_modifiables(champ_id, date_limite, filtrer_non_joues)

if matchs_simulables.empty:
    st.info("Aucun match à afficher pour cette configuration.")
else:
    st.markdown("### Matchs simulables")

    # Copie modifiable du DataFrame
    df_simulation = matchs_simulables.copy()

    # Zone d'édition des scores
    edited_df = st.data_editor(
        df_simulation[[
            "ID_MATCH", "JOURNEE", "POULE", "DATE",
            "EQUIPE_DOM", "NB_BUT_DOM", "EQUIPE_EXT", "NB_BUT_EXT", "STATUT"
        ]],
        num_rows="dynamic",
        use_container_width=True,
        key="simulation_scores"
    )

    # Bouton pour recalculer
    if st.button("🔁 Recalculer le classement avec ces scores simulés"):
        st.session_state["simulated_scores"] = edited_df
        st.success("Scores pris en compte. On peut maintenant recalculer le classement.")
