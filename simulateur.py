import streamlit as st
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account

st.set_page_config(page_title="Simulateur Datafoot", layout="wide")

# Connexion à BigQuery
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"]
)
client = bigquery.Client(credentials=credentials, project=credentials.project_id)

st.title("⚽ Simulateur de classement - Datafoot")

# Sélection du championnat
@st.cache_data
def get_liste_championnats():
    query = """
        SELECT ID_CHAMPIONNAT, NOM_CHAMPIONNAT, CATEGORIE, NIVEAU
        FROM `datafoot-448514.DATAFOOT.DATAFOOT_CHAMPIONNAT`
        ORDER BY CATEGORIE, NIVEAU, NOM_CHAMPIONNAT
    """
    return client.query(query).to_dataframe()

champ_df = get_liste_championnats()
champ_df["LABEL"] = champ_df["CATEGORIE"] + " - " + champ_df["NIVEAU"] + " - " + champ_df["NOM_CHAMPIONNAT"]
selected_label = st.selectbox("Sélectionnez un championnat", champ_df["LABEL"])
selected_id_championnat = champ_df[champ_df["LABEL"] == selected_label]["ID_CHAMPIONNAT"].values[0]

# Sélection de la date
date_limite = st.date_input("Date de simulation", value=pd.to_datetime("2025-03-31"))

# Requête classement réel (à la dernière date disponible avant la sélection)
@st.cache_data
def get_classement_reel(date, id_championnat):
    query_date = f"""
        SELECT MAX(DATE_CALCUL) AS DERNIERE_DATE
        FROM `datafoot-448514.DATAFOOT.VIEW_CLASSEMENT_REEL_2025`
        WHERE DATE_CALCUL <= DATE('{date}')
          AND ID_CHAMPIONNAT = '{id_championnat}'
    """
    result = client.query(query_date).to_dataframe()
    if result.empty or pd.isna(result.iloc[0]["DERNIERE_DATE"]):
        return pd.DataFrame()
    date_finale = result.iloc[0]["DERNIERE_DATE"]

    query = f"""
        SELECT *
        FROM `datafoot-448514.DATAFOOT.VIEW_CLASSEMENT_REEL_2025`
        WHERE DATE_CALCUL = DATE('{date_finale}')
          AND ID_CHAMPIONNAT = '{id_championnat}'
        ORDER BY POULE, RANG
    """
    return client.query(query).to_dataframe()

# Requête classement simulé
@st.cache_data
def get_classement_simule(date, id_championnat):
    query = f"""
        SELECT *
        FROM `datafoot-448514.DATAFOOT.VIEW_CLASSEMENT_DYNAMIQUE`
        WHERE DATE_CALCUL = DATE('{date}')
          AND ID_CHAMPIONNAT = '{id_championnat}'
        ORDER BY POULE, RANG
    """
    return client.query(query).to_dataframe()

# Récupération des données
classement_reel = get_classement_reel(date_limite, selected_id_championnat)
classement_simule = get_classement_simule(date_limite, selected_id_championnat)

# Affichage
st.header("📊 Comparaison des classements")
if classement_reel.empty and classement_simule.empty:
    st.warning("Aucun classement disponible pour ce championnat à cette date.")
else:
    poules = classement_simule["POULE"].unique() if not classement_simule.empty else classement_reel["POULE"].unique()
    for poule in sorted(poules):
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
