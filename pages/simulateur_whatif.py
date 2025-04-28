import streamlit as st
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account

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
    get_matchs_modifiables,
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

classement_df = None
mini_classements = {}

if st.button("🔁 Recalculer le classement avec ces scores simulés"):
    st.session_state["simulated_scores"] = edited_df

    df_valid = edited_df.dropna(subset=["NB_BUT_DOM", "NB_BUT_EXT"])
    df_valid["ID_CHAMPIONNAT"] = champ_id
    st.write("🧪 Scores simulés transmis :", df_valid)

    if df_valid.empty:
        st.warning("🚫 Aucun score simulé valide.")
    else:
        classement_df, mini_classements = recalculer_classement_simule(df_valid, champ_id, date_limite, selected_poule, type_classement)

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

# 📌 Cas particuliers (U19 / U17 / N2 / N3)
if classement_df is not None and selected_poule == "Toutes les poules":
    if champ_id == 6 and not classement_df.empty:
        st.markdown("### 🚨 Classement spécial des 11èmes (règle U19 National)")
        df_11e_comp = classement_special_u19(classement_df, champ_id, date_limite)
        if df_11e_comp is not None:
            st.dataframe(df_11e_comp, use_container_width=True)

    if champ_id == 7 and not classement_df.empty:
        st.markdown("### 🥈 Comparatif des 2e (règle U17 National)")
        df_2e_comp = classement_special_u17(classement_df, champ_id, date_limite)
        if df_2e_comp is not None:
            st.dataframe(df_2e_comp, use_container_width=True)

    if champ_id == 4 and not classement_df.empty:
        st.markdown("### 🚨 Comparatif des 13e (règle N2)")
        df_13e_comp = classement_special_n2(classement_df, champ_id, date_limite)
        if df_13e_comp is not None:
            st.dataframe(df_13e_comp, use_container_width=True)

    if champ_id == 5 and not classement_df.empty:
        st.markdown("### ⚠️ Comparatif des 10e (règle N3)")
        df_10e_comp = classement_special_n3(classement_df, champ_id, date_limite)
        if df_10e_comp is not None:
            st.dataframe(df_10e_comp, use_container_width=True)

else:
    if champ_id in [4, 5, 6, 7]:
        st.info("🔒 Les règles spécifiques (U19, U17, N2, N3) ne sont disponibles que si toutes les poules sont affichées.")

# --------------------------------------------------------
# Fonction utilisée pour l'application Datafoot (app.py)
# --------------------------------------------------------

def afficher_simulateur_whatif():
    st.title("Simulation de Classement 🔮")

    championnats = load_championnats()
    selected_championnat = st.selectbox("Sélectionnez un championnat à simuler :", championnats['NOM_CHAMPIONNAT'])

    if selected_championnat:
        id_championnat = championnats.loc[championnats['NOM_CHAMPIONNAT'] == selected_championnat, 'ID_CHAMPIONNAT'].values[0]

        matchs = get_matchs_modifiables(id_championnat)

        if not matchs.empty:
            st.markdown("### Modifiez les scores si nécessaire :")
            matchs_modifies = appliquer_scores_simules(matchs)

            if st.button("🔄 Recalculer le Classement Simulé"):
                classement, mini_classements = recalculer_classement_simule(matchs_modifies, id_championnat)

                if classement is not None and not classement.empty:
                    st.success("Classement simulé recalculé avec succès !")

                    poules_dispo = classement['POULE'].unique()
                    for poule in sorted(poules_dispo):
                        st.markdown(f"### Poule {poule}")
                        classement_poule = classement[classement["POULE"] == poule]

                        colonnes_souhaitées = [
                            "CLASSEMENT", "NOM_EQUIPE", "POINTS",
                            "PENALITES", "G", "N", "P", "BP", "BC", "DIFF"
                        ]
                        colonnes_finales = [col for col in colonnes_souhaitées if col in classement_poule.columns]
                        st.dataframe(classement_poule[colonnes_finales], use_container_width=True)

                    # --- Mini-classements affichés aussi
                    st.markdown("## 🔥 Détails des Égalités Particulières")
                    for (poule, pts), mini in mini_classements.items():
                        st.markdown(f"#### Poule {poule} - {pts} points")
                        st.dataframe(mini["classement"], use_container_width=True)
                        st.dataframe(mini["matchs"], use_container_width=True)

                else:
                    st.warning("Impossible de recalculer le classement simulé.")
        else:
            st.warning("Aucun match disponible pour simulation dans ce championnat.")

    # --- Retour à l'accueil ---
    st.markdown("---")
    if st.button("⬅️ Retour à l'accueil"):
        st.session_state.page = "home"
