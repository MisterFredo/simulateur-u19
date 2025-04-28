import streamlit as st
import pandas as pd
from datetime import date
from google.cloud import bigquery
from google.oauth2 import service_account

from simulateur_core import (
    load_championnats,
    get_matchs_modifiables,
    get_poules_temp,
    get_matchs_termine,
    get_classement_dynamique,
    appliquer_penalites,
    appliquer_diff_particuliere,
    trier_et_numeroter,
    get_type_classement,
    classement_special_u19,
    classement_special_u17,
    classement_special_n2,
    classement_special_n3,
)

# --- CONFIG STREAMLIT
st.set_page_config(page_title="SIMULATEUR - Datafoot", layout="wide")

# --- Connexion BigQuery
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"]
)
client = bigquery.Client(credentials=credentials, project=credentials.project_id)

# --- Chargement championnats
championnats_df = load_championnats()

# --- SIDEBAR
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

type_classement = get_type_classement(champ_id)

poules_temp = get_poules_temp(champ_id)
all_poules = sorted(poules_temp["POULE"].dropna().unique())

if len(all_poules) > 1:
    selected_poule = st.sidebar.selectbox("Poule", ["Toutes les poules"] + all_poules)
else:
    selected_poule = all_poules[0] if all_poules else "Toutes les poules"

date_limite = st.sidebar.date_input("Date de simulation", value=date.today())

# --- Titre
st.title(f"🧪 Simulateur – {selected_nom}")

# --- Chargement matchs simulables
filtrer_non_joues = st.checkbox("Afficher uniquement les matchs non joués", value=True)

matchs_simulables = get_matchs_modifiables(champ_id, date_limite, filtrer_non_joues)

if selected_poule != "Toutes les poules":
    matchs_simulables = matchs_simulables[matchs_simulables["POULE"] == selected_poule]

if matchs_simulables.empty:
    st.info("Aucun match à afficher pour cette configuration.")
    st.stop()

st.markdown("### Matchs simulables")
edited_df = st.data_editor(
    matchs_simulables[[
        "ID_MATCH", "JOURNEE", "POULE", "DATE",
        "ID_EQUIPE_DOM", "EQUIPE_DOM", "NB_BUT_DOM",
        "ID_EQUIPE_EXT", "EQUIPE_EXT", "NB_BUT_EXT"
    ]],
    num_rows="dynamic",
    use_container_width=True,
    key="simulation_scores"
)

def recalculer_classement_simule(matchs_modifies, champ_id, date_limite, selected_poule, type_classement):

    # 1. Charger les vrais matchs terminés
    matchs_officiels = get_matchs_termine(champ_id, date_limite)

    if matchs_officiels.empty:
        return pd.DataFrame(), {}

    # 2. Remplacer les scores pour les matchs simulés
    matchs_simules = matchs_officiels.copy()
    for idx, row in matchs_modifies.iterrows():
        id_match = row["ID_MATCH"]
        if id_match in matchs_simules["ID_MATCH"].values:
            matchs_simules.loc[matchs_simules["ID_MATCH"] == id_match, "NB_BUT_DOM"] = row["NB_BUT_DOM"]
            matchs_simules.loc[matchs_simules["ID_MATCH"] == id_match, "NB_BUT_EXT"] = row["NB_BUT_EXT"]

    # 3. Recalculer le classement dynamique basé sur les scores simulés
    classement_df = get_classement_dynamique(champ_id, date_limite, matchs_override=matchs_simules)

    if classement_df.empty:
        return classement_df, {}

    # 4. Appliquer pénalités et égalités particulières
    classement_df = appliquer_penalites(classement_df, date_limite)
    classement_df, mini_classements = appliquer_diff_particuliere(classement_df, matchs_simules)

    # 5. Trier et numéroter
    classement_df = trier_et_numeroter(classement_df, type_classement)

    # 6. Si besoin, filtrer par poule simulée
    if selected_poule != "Toutes les poules":
        classement_df = classement_df[classement_df["POULE"] == selected_poule]

    return classement_df, mini_classements

# --- Mini-classements
if mini_classements:
    st.markdown("### Mini-classements des égalités particulières 🥇")
    for (poule, pts), mini in mini_classements.items():
        with st.expander(f"Poule {poule} – Égalité à {pts} points", expanded=True):
            st.markdown("**Mini-classement :**")
            st.dataframe(mini["classement"], use_container_width=True)
            st.markdown("**Matchs concernés :**")
            st.dataframe(mini["matchs"], use_container_width=True)

# --- Cas particuliers
if classement_df is not None and selected_poule == "Toutes les poules":
    if champ_id == 6:
        st.markdown("### 🚨 Comparatif spécial U19")
        df_11e = classement_special_u19(classement_df, champ_id, date_limite)
        if df_11e is not None:
            st.dataframe(df_11e, use_container_width=True)

    if champ_id == 7:
        st.markdown("### 🥈 Comparatif spécial U17")
        df_2e = classement_special_u17(classement_df, champ_id, date_limite)
        if df_2e is not None:
            st.dataframe(df_2e, use_container_width=True)

    if champ_id == 4:
        st.markdown("### 🚨 Comparatif spécial N2")
        df_13e = classement_special_n2(classement_df, champ_id, date_limite)
        if df_13e is not None:
            st.dataframe(df_13e, use_container_width=True)

    if champ_id == 5:
        st.markdown("### ⚠️ Comparatif spécial N3")
        df_10e = classement_special_n3(classement_df, champ_id, date_limite)
        if df_10e is not None:
            st.dataframe(df_10e, use_container_width=True)
