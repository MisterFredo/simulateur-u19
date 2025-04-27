import streamlit as st
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account

# Fonctions locales importées depuis simulateur_core.py
from simulateur_core import (
    get_classement_dynamique,
    get_type_classement,
    appliquer_diff_particuliere,
    get_matchs_termine,
    get_poules_temp,
    load_championnats,
    appliquer_penalites,
    trier_et_numeroter,
    classement_special_u19,
    classement_special_u17,
    classement_special_n2,
    classement_special_n3,
)

# 🎛️ Configuration
st.set_page_config(page_title="Classement - Datafoot", layout="wide")

# 🔌 Connexion BigQuery
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"]
)
client = bigquery.Client(credentials=credentials, project=credentials.project_id)

# 📋 Chargement des championnats
championnats_df = load_championnats()

# 🎚️ Filtres utilisateurs
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

# 🏷️ Affichage du titre
st.title(f"Classement – {selected_nom}")

# 🧾 Chargement des poules
poules_temp = get_poules_temp(champ_id)
all_poules = sorted(poules_temp["POULE"].dropna().unique())
if len(all_poules) > 1:
    selected_poule = st.sidebar.selectbox("Poule", ["Toutes les poules"] + all_poules)
else:
    selected_poule = all_poules[0] if all_poules else "Toutes les poules"

# 🗓️ Date limite
date_limite = st.sidebar.date_input("Date de simulation", value=pd.to_datetime("2025-06-30"))

# 🔢 Classement brut
classement_complet = get_classement_dynamique(champ_id, date_limite)
classement_df = classement_complet.copy()

# 🧮 Application des pénalités
classement_df = appliquer_penalites(classement_df, date_limite)

# 📌 Détection du type de classement
type_classement = get_type_classement(champ_id)

# 💬 Message d'information
if type_classement == "PARTICULIERE":
    st.caption("📌 Les égalités sont traitées selon le principe de la différence particulière (points puis différence de buts).")
    st.caption("📌 Pour le détail du calcul des départages des égalités, sélectionner une Poule.")

# 🧪 Application des égalités particulières si besoin
matchs = get_matchs_termine(champ_id, date_limite)
if type_classement == "PARTICULIERE":
    classement_df, mini_classements = appliquer_diff_particuliere(classement_df, matchs, selected_poule)
else:
    mini_classements = {}

# 🧮 Tri et numérotation finale
classement_df = trier_et_numeroter(classement_df, type_classement)

# 🔍 Filtrage si une seule poule est sélectionnée
if selected_poule != "Toutes les poules":
    classement_df = classement_df[classement_df["POULE"] == selected_poule]

# 📊 Affichage du classement principal
if classement_df.empty:
    st.warning("Aucun classement disponible pour ces critères.")
else:
    for poule in sorted(classement_df["POULE"].unique()):
        st.subheader(f"Poule {poule}")
        df = classement_df[classement_df["POULE"] == poule][[
            "CLASSEMENT", "NOM_EQUIPE", "POINTS", "PENALITES", "MJ", "G", "N", "P", "BP", "BC", "DIFF"
        ]].rename(columns={"MJ": "J."})
        st.dataframe(df, use_container_width=True)

# 📌 Mini-classements détaillés
if selected_poule != "Toutes les poules" and mini_classements:
    st.markdown("## Mini-classements (en cas d’égalité)")
    for (poule, pts), data in mini_classements.items():
        st.markdown(f"### Poule {poule} — Égalité à {pts} pts")
        st.markdown("**Mini-classement**")
        st.dataframe(data["classement"])
        st.markdown("**Matchs concernés**")
        st.dataframe(data["matchs"])

# 📌 U19 : moins bon 11ème
if selected_poule == "Toutes les poules" and champ_id == 6:
    st.markdown("### 🚨 Classement spécial des 11èmes (règle U19 National)")
    df_11e_comp = classement_special_u19(classement_df, champ_id, date_limite)
    if df_11e_comp is not None:
        st.dataframe(df_11e_comp, use_container_width=True)

# 📌 U17 : meilleurs 2ème
if selected_poule == "Toutes les poules" and champ_id == 7:
    st.markdown("### 🥈 Comparatif des 2e (règle U17 National)")
    df_2e_comp = classement_special_u17(classement_df, champ_id, client)
    if df_2e_comp is not None:
        st.dataframe(df_2e_comp, use_container_width=True)

# 📌 N2 : moins bon 13ème
if selected_poule == "Toutes les poules" and champ_id == 4:
    st.markdown("### 🚨 Comparatif des 13e (règle N2)")
    df_13e_comp = classement_special_n2(classement_df, champ_id, date_limite)
    if df_13e_comp is not None:
        st.dataframe(df_13e_comp, use_container_width=True)

# 📌 N2 : moins bon 10ème
if selected_poule == "Toutes les poules" and champ_id == 5:
    st.markdown("### ⚠️ Comparatif des 10e (règle N3)")
    df_10e_comp = classement_special_n3(classement_df, champ_id, date_limite)
    if df_10e_comp is not None:
        st.dataframe(df_10e_comp, use_container_width=True)

# Cas particuliers (U19 / U17 / N2)
if selected_poule == "Toutes les poules":
    # 👉 Toutes les règles spéciales sont déjà appelées ci-dessus
    pass
else:
    if champ_id in [4, 5, 6, 7]:
        st.info("🔒 Les règles spécifiques (U19, U17, N2, N3) ne sont disponibles que si toutes les poules sont affichées.")

# === Fonction d'entrée pour app.py ===
def afficher_classement():
    st.title("Classements Officiels ⚽")

    championnats = load_championnats()

    selected_championnat = st.selectbox("Sélectionnez un championnat :", championnats['NOM_CHAMPIONNAT'])

    if selected_championnat:
        id_championnat = championnats.loc[championnats['NOM_CHAMPIONNAT'] == selected_championnat, 'ID_CHAMPIONNAT'].values[0]

        matchs = get_matchs_termine(id_championnat)

        classement = get_classement_dynamique(matchs)

        classement = appliquer_penalites(classement)

        classement = appliquer_diff_particuliere(classement)

        classement = trier_et_numeroter(classement)

        st.dataframe(classement, use_container_width=True)
        
        st.title("Classements Officiels ⚽")
    ...

    # --- Affichage du classement ---
    st.dataframe(classement, use_container_width=True)

    # --- Retour à l'accueil ---
    st.markdown("---")
    if st.button("⬅️ Retour à l'accueil"):
        st.session_state.page = "home"



