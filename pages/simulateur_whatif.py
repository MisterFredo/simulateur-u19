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

# --- INIT SESSION STATE
if "simulation_validee" not in st.session_state:
    st.session_state.simulation_validee = False

# --- Connexion BigQuery
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"]
)
client = bigquery.Client(credentials=credentials, project=credentials.project_id)

# --- Chargement championnats
championnats_df = load_championnats()

# --- SIDEBAR (Filtres)
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

# --- TITRE
st.title(f"🧪 Simulateur – {selected_nom}")

# --- 1. CLASSEMENT ACTUEL
matchs_termine = get_matchs_termine(champ_id, date_limite)
classement_initial = get_classement_dynamique(champ_id, date_limite, matchs_override=matchs_termine)
classement_initial = appliquer_penalites(classement_initial, date_limite)
classement_initial = trier_et_numeroter(classement_initial, type_classement)

st.markdown("### 🏆 Classement actuel")
for poule in sorted(classement_initial["POULE"].unique()):
    st.subheader(f"Poule {poule}")
    classement_poule = classement_initial[classement_initial["POULE"] == poule]
    colonnes = ["CLASSEMENT", "NOM_EQUIPE", "POINTS", "PENALITES", "MJ", "G", "N", "P", "BP", "BC", "DIFF"]
    colonnes_finales = [col for col in colonnes if col in classement_poule.columns]
    st.dataframe(classement_poule[colonnes_finales], use_container_width=True)

# --- 2. MINI-CLASSEMENTS ACTUELS
classement_initial, mini_classements_initial = appliquer_diff_particuliere(classement_initial, matchs_termine)

if mini_classements_initial:
    st.markdown("### Mini-classements des égalités particulières 🥇 (Classement actuel)")
    for (poule, pts), mini in mini_classements_initial.items():
        with st.expander(f"Poule {poule} – Égalité à {pts} points", expanded=True):
            st.markdown("**Mini-classement :**")
            st.dataframe(mini["classement"], use_container_width=True)
            st.markdown("**Matchs concernés :**")
            st.dataframe(mini["matchs"], use_container_width=True)

# --- 3. MATCHS À SIMULER
filtrer_non_joues = st.checkbox("Afficher uniquement les matchs non joués", value=True)

matchs_simulables = get_matchs_modifiables(champ_id, date_limite, filtrer_non_joues)

if selected_poule != "Toutes les poules":
    matchs_simulables = matchs_simulables[matchs_simulables["POULE"] == selected_poule]

st.markdown("### 🎯 Matchs à simuler")
if matchs_simulables.empty:
    st.info("Aucun match disponible pour cette configuration.")
    st.stop()

# --- Data editor simplifié
edited_df = st.data_editor(
    matchs_simulables[[
        "JOURNEE", "POULE", "DATE",
        "EQUIPE_DOM", "NB_BUT_DOM",
        "EQUIPE_EXT", "NB_BUT_EXT"
    ]],
    num_rows="dynamic",
    use_container_width=True,
    key="simulation_scores"
)

# --- 4. VALIDATION SIMULATION PAR CLIC
if st.button("🔁 Recalculer le classement avec ces scores simulés"):
    st.session_state.simulation_validee = True

# --- 5. SIMULATION SEULEMENT SI VALIDATION
if st.session_state.simulation_validee:

    df_valid = edited_df.dropna(subset=["NB_BUT_DOM", "NB_BUT_EXT"])

    if df_valid.empty:
        st.warning("🚫 Aucun score simulé valide.")
    else:
        # --- Affichage des matchs simulés pour rappel
        st.markdown("### 📝 Matchs simulés")
        def color_victory(val_dom, val_ext):
            if val_dom > val_ext:
                return ["background-color: lightgreen", "background-color: lightcoral"]
            elif val_dom < val_ext:
                return ["background-color: lightcoral", "background-color: lightgreen"]
            else:
                return ["background-color: lightyellow", "background-color: lightyellow"]

        matchs_affichage = df_valid[[
            "JOURNEE", "POULE", "DATE", "EQUIPE_DOM", "NB_BUT_DOM", "EQUIPE_EXT", "NB_BUT_EXT"
        ]].copy()

        if not matchs_affichage.empty:
            styled_matchs = matchs_affichage.style.apply(
                lambda row: color_victory(row["NB_BUT_DOM"], row["NB_BUT_EXT"]),
                subset=["NB_BUT_DOM", "NB_BUT_EXT"],
                axis=1
            )
            st.dataframe(styled_matchs, use_container_width=True)

        # --- Fusion des matchs terminés + matchs simulables
        matchs_tous = pd.concat([matchs_termine, matchs_simulables], ignore_index=True)

        # --- Remplacer uniquement les scores réellement simulés
        for idx, row in df_valid.iterrows():
            id_match = matchs_simulables.iloc[idx]["ID_MATCH"]
            if not pd.isna(row["NB_BUT_DOM"]) and not pd.isna(row["NB_BUT_EXT"]):
                matchs_tous.loc[matchs_tous["ID_MATCH"] == id_match, "NB_BUT_DOM"] = int(row["NB_BUT_DOM"])
                matchs_tous.loc[matchs_tous["ID_MATCH"] == id_match, "NB_BUT_EXT"] = int(row["NB_BUT_EXT"])

        # --- Sécurisation
        matchs_tous = matchs_tous.dropna(subset=["NB_BUT_DOM", "NB_BUT_EXT"])

        # --- Recalcul du classement
        classement_simule = get_classement_dynamique(champ_id, date_limite, matchs_override=matchs_tous)
        classement_simule = appliquer_penalites(classement_simule, date_limite)
        classement_simule, mini_classements_simule = appliquer_diff_particuliere(classement_simule, matchs_tous)
        classement_simule = trier_et_numeroter(classement_simule, type_classement)

        # --- Confirmation
        st.success("✅ Simulation recalculée avec succès !")

        # --- Affichage du nouveau classement simulé
        st.markdown("### 🧪 Nouveau Classement simulé")
        for poule in sorted(classement_simule["POULE"].unique()):
            st.subheader(f"Poule {poule}")
            classement_poule = classement_simule[classement_simule["POULE"] == poule]
            colonnes_finales = [col for col in colonnes if col in classement_poule.columns]
            st.dataframe(classement_poule[colonnes_finales], use_container_width=True)

        # --- Mini-classements simulés
        if mini_classements_simule:
            st.markdown("### Mini-classements des égalités particulières 🥇 (Simulation)")
            for (poule, pts), mini in mini_classements_simule.items():
                with st.expander(f"Poule {poule} – Égalité à {pts} points", expanded=True):
                    st.markdown("**Mini-classement :**")
                    st.dataframe(mini["classement"], use_container_width=True)
                    st.markdown("**Matchs concernés :**")
                    st.dataframe(mini["matchs"], use_container_width=True)

        # --- Comparatifs spéciaux
        if selected_poule == "Toutes les poules":
            if champ_id == 6:
                st.markdown("### 🚨 Comparatif spécial U19")
                df_11e = classement_special_u19(classement_simule, champ_id, date_limite)
                if df_11e is not None:
                    st.dataframe(df_11e, use_container_width=True)

            if champ_id == 7:
                st.markdown("### 🥈 Comparatif spécial U17")
                df_2e = classement_special_u17(classement_simule, champ_id, date_limite)
                if df_2e is not None:
                    st.dataframe(df_2e, use_container_width=True)

            if champ_id == 4:
                st.markdown("### 🚨 Comparatif spécial N2")
                df_13e = classement_special_n2(classement_simule, champ_id, date_limite)
                if df_13e is not None:
                    st.dataframe(df_13e, use_container_width=True)

            if champ_id == 5:
                st.markdown("### ⚠️ Comparatif spécial N3")
                df_10e = classement_special_n3(classement_simule, champ_id, date_limite)
                if df_10e is not None:
                    st.dataframe(df_10e, use_container_width=True)
