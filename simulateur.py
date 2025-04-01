import streamlit as st
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account

# Configuration de la page
st.set_page_config(page_title="Classement - Datafoot", layout="wide")

# Connexion à BigQuery via secrets
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

# Filtres latéraux
st.sidebar.header("Filtres")
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

date_limite = st.sidebar.date_input("Date de simulation", value=pd.to_datetime("2025-03-31"))

# Récupération du classement via la vue à jour
@st.cache_data(show_spinner=False)
def get_classement_par_date(id_championnat, date):
    query = f"""
        SELECT *
        FROM `datafoot-448514.DATAFOOT.VIEW_CLASSEMENT_PAR_DATE`
        WHERE ID_CHAMPIONNAT = {id_championnat}
          AND DATE <= DATE('{date}')
        ORDER BY POULE, CLASSEMENT
    """
    return client.query(query).to_dataframe()

classement_df = get_classement_par_date(champ_id, date_limite)

# Affichage
st.title("🏆 Classement - Datafoot")
st.markdown(f"### {selected_nom} ({selected_categorie} - {selected_niveau}) au {date_limite.strftime('%d/%m/%Y')}")

if classement_df.empty:
    st.warning("Aucun classement disponible pour ces critères.")
else:
    for poule in sorted(classement_df["POULE"].unique()):
        st.subheader(f"Poule {poule}")
        df = classement_df[classement_df["POULE"] == poule][[
            "CLASSEMENT", "NOM_EQUIPE", "PTS", "BP", "BC", "DIFF", "MJ"
        ]].rename(columns={
            "PTS": "POINTS", "BP": "BUTS_POUR", "BC": "BUTS_CONTRE", "MJ": "MATCHS_JOUES"
        })
        st.dataframe(df, use_container_width=True)

st.caption("💡 Classement calculé à partir des matchs terminés uniquement, selon la date sélectionnée.")
