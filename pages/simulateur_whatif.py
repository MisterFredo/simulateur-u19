import streamlit as st
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account

# Fonctions locales importées depuis simulateur_core.py
from simulateur_core import (
    recalculer_classement_simule,
    appliquer_penalites,
    load_championnats,
    get_type_classement,
    get_poules_temp,
    trier_et_numeroter,
    appliquer_diff_particuliere,
    classement_special_u19,
    classement_special_u17,
    classement_special_n2,
    classement_special_n3,
)

# Configuration Streamlit
st.set_page_config(page_title="SIMULATEUR - Datafoot", layout="wide")

# Connexion à BigQuery via secrets
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"]
)
client = bigquery.Client(credentials=credentials, project=credentials.project_id)

# Chargement des championnats
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

# On peut maintenant appeler la fonction qui a besoin de champ_id
type_classement = get_type_classement(champ_id)


# Affichage du titre
st.title(f"🧪 Simulateur – {selected_nom}")

from simulateur_core import get_poules_temp

# Chargement des poules
poules_temp = get_poules_temp(champ_id)
all_poules = sorted(poules_temp["POULE"].dropna().unique())

if len(all_poules) > 1:
    selected_poule = st.sidebar.selectbox("Poule", ["Toutes les poules"] + all_poules)
else:
    selected_poule = all_poules[0] if all_poules else "Toutes les poules"

# Date de simulation
import datetime
date_limite = st.sidebar.date_input("Date de simulation", value=datetime.date.today())

# 🔐 Initialisation pour éviter les erreurs si bouton pas cliqué
mini_classements = {}

# Affichage des matchs modifiables
from simulateur_core import get_matchs_modifiables

filtrer_non_joues = st.checkbox("Afficher uniquement les matchs non joués", value=True)

matchs_simulables = get_matchs_modifiables(champ_id, date_limite, filtrer_non_joues)

if selected_poule != "Toutes les poules":
    matchs_simulables = matchs_simulables[matchs_simulables["POULE"] == selected_poule]

if matchs_simulables.empty:
    st.info("Aucun match à afficher pour cette configuration.")
else:
    st.markdown("### Matchs simulables")
    df_simulation = matchs_simulables.copy()
    edited_df = st.data_editor(
    df_simulation[[
        "ID_MATCH", "JOURNEE", "POULE", "DATE",
        "ID_EQUIPE_DOM", "EQUIPE_DOM", "NB_BUT_DOM",
        "ID_EQUIPE_EXT", "EQUIPE_EXT", "NB_BUT_EXT"
    ]],
    num_rows="dynamic",
    use_container_width=True,
    key="simulation_scores"
)


if st.button("🔁 Recalculer le classement avec ces scores simulés"):
    st.session_state["simulated_scores"] = edited_df

    df_valid = edited_df.dropna(subset=["NB_BUT_DOM", "NB_BUT_EXT"])
    df_valid["ID_CHAMPIONNAT"] = champ_id
    st.write("🧪 Scores simulés transmis :", df_valid)

    if df_valid.empty:
        st.warning("🚫 Aucun score simulé valide.")
    else:
        classement_df, mini_classements = recalculer_classement_simule(df_valid, champ_id, date_limite, selected_poule, type_classement)
        st.write("🧪 Colonnes dans classement_df :", classement_df.columns.tolist())

        if classement_df.empty:
            st.warning("🚫 Aucun classement n'a pu être généré.")
        else:
            for poule in sorted(classement_df["POULE"].unique()):
                st.subheader(f"Poule {poule}")
                st.dataframe(
                    classement_df[classement_df["POULE"] == poule][[
                        "CLASSEMENT", "NOM_EQUIPE", "POINTS", "PENALITES", "MJ", "G", "N", "P", "BP", "BC", "DIFF"
                    ]],
                    use_container_width=True
                )

if selected_poule != "Toutes les poules" and mini_classements:
    st.markdown("## ⚖️ Mini-classements (en cas d’égalité)")
    for (poule, pts), data in mini_classements.items():
        with st.expander(f"📋 Poule {poule} – Égalité à {pts} points", expanded=True):
            st.markdown("**Mini-classement :**")
            st.dataframe(data["classement"], use_container_width=True)
            st.markdown("**Matchs concernés :**")
            st.dataframe(data["matchs"], use_container_width=True)

