import streamlit as st
import pandas as pd
from datetime import date
from google.cloud import bigquery
from google.oauth2 import service_account
import sys
import os

# Ajout du chemin vers simulateur_core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

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
    calculer_difficulte_calendrier,
    recalculer_classement_simule
)

# --- CONFIG STREAMLIT ---
st.set_page_config(page_title="SIMULATEUR - Datafoot", layout="wide")

# --- STYLE UNIFIE AVEC LA PAGE D'ACCUEIL ---
st.markdown(
    """
    <style>
    [data-testid="stAppViewContainer"] {
        background-color: #ffffff;
        padding: 2rem;
    }
    h1, h2, h3 {
        color: #2E3C51;
        font-family: 'Poppins', 'Segoe UI', sans-serif;
    }
    img {
        height: auto !important;
        max-width: 100%;
    }
    .stButton>button {
        border-radius: 8px;
        padding: 0.5rem 1rem;
        background-color: #0066cc;
        color: white;
        border: none;
    }
    .stButton>button:hover {
        background-color: #005bb5;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# --- FONCTION AFFICHAGE COMPARATIFS SPÉCIAUX ---
def afficher_comparatifs_speciaux(champ_id, classement_df, date_limite):
    if champ_id == 6:
        st.markdown("### Comparatif spécial U19")
        df_11e = classement_special_u19(classement_df, champ_id, date_limite)
        if df_11e is not None:
            st.dataframe(df_11e, use_container_width=True, hide_index=True)

    if champ_id == 7:
        st.markdown("### Comparatif spécial U17")
        df_2e = classement_special_u17(classement_df, champ_id, date_limite)
        if df_2e is not None:
            st.dataframe(df_2e, use_container_width=True, hide_index=True)

    if champ_id == 4:
        st.markdown("### Comparatif spécial N2")
        df_13e = classement_special_n2(classement_df, champ_id, date_limite)
        if df_13e is not None:
            st.dataframe(df_13e, use_container_width=True, hide_index=True)

    if champ_id == 5:
        st.markdown("### Comparatif spécial N3")
        df_10e = classement_special_n3(classement_df, champ_id, date_limite)
        if df_10e is not None:
            st.dataframe(df_10e, use_container_width=True, hide_index=True)

# --- FACTORISATION MINI-CLASSEMENTS ---
def afficher_mini_classements_bloc(mini_classements, titre_bloc):
    st.markdown(titre_bloc)
    for (poule, pts), mini in mini_classements.items():
        with st.expander(f"Poule {poule} – Égalité à {pts} points", expanded=True):
            st.markdown("**Mini-classement :**")
            df_mini = mini["classement"].copy()
            colonnes_mini = [col for col in df_mini.columns if col != "CLASSEMENT"]
            st.dataframe(df_mini[colonnes_mini], use_container_width=True, hide_index=True)

            st.markdown("**Matchs concernés :**")
            df_matchs = mini["matchs"].copy()
            st.dataframe(df_matchs.reset_index(drop=True), use_container_width=True, hide_index=True)

# --- INIT SESSION STATE ---
if "simulation_validee" not in st.session_state:
    st.session_state.simulation_validee = False

# --- Chargement championnats ---
championnats_df = load_championnats()


# --- SIDEBAR (Filtres) ---
st.sidebar.header("Filtres")

selected_categorie = st.sidebar.selectbox(
    "Catégorie",
    sorted(championnats_df["CATEGORIE"].unique())
)

selected_niveau = st.sidebar.selectbox(
    "Niveau",
    sorted(championnats_df[championnats_df["CATEGORIE"] == selected_categorie]["NIVEAU"].unique())
)

champ_options = championnats_df[
    (championnats_df["CATEGORIE"] == selected_categorie) &
    (championnats_df["NIVEAU"] == selected_niveau)
]

selected_nom = st.sidebar.selectbox("Championnat", champ_options["NOM_CHAMPIONNAT"])

champ_selected = champ_options[champ_options["NOM_CHAMPIONNAT"] == selected_nom]
champ_id = champ_selected["ID_CHAMPIONNAT"].values[0]
champ_type_classement = champ_selected["CLASSEMENT"].values[0]

type_classement = get_type_classement(champ_id)

poules_temp = get_poules_temp(champ_id)
all_poules = sorted(poules_temp["POULE"].dropna().unique())

if len(all_poules) > 1:
    selected_poule = st.sidebar.selectbox("Poule", ["Toutes les poules"] + all_poules)
else:
    selected_poule = all_poules[0] if all_poules else "Toutes les poules"

# --- Par défaut : date au 30 juin ---
date_limite = st.sidebar.date_input("Date de simulation", value=date(2025, 6, 30))

# --- TITRE PRINCIPAL ---
st.markdown(f"## Simulateur – {selected_nom}")
st.markdown("Explorez les scénarios, les classements et les règles spéciales.")
st.markdown("---")

# --- Choix Mode Simplifié ---
mode_simplifie = st.toggle("Afficher en mode simplifié (affichage mobile optimisé)", value=True)

colonnes_completes = ["CLASSEMENT", "NOM_EQUIPE", "POINTS", "PENALITES", "MJ", "G", "N", "P", "BP", "BC", "DIFF"]
colonnes_simplifiees = ["CLASSEMENT", "NOM_EQUIPE", "POINTS", "DIFF", "MJ"]


# --- Classement actuel ---
matchs_termine = get_matchs_termine(champ_id, date_limite)
matchs_restants = get_matchs_modifiables(champ_id, date_limite, True)

classement_initial = get_classement_dynamique(champ_id, date_limite, matchs_override=matchs_termine)
classement_initial = appliquer_penalites(classement_initial, date_limite)

if champ_type_classement == "PARTICULIERE":
    classement_initial, mini_classements_initial = appliquer_diff_particuliere(classement_initial, matchs_termine)

classement_initial = trier_et_numeroter(classement_initial, type_classement)
classement_initial = calculer_difficulte_calendrier(classement_initial, matchs_restants)

if selected_poule != "Toutes les poules":
    classement_initial = classement_initial[classement_initial["POULE"] == selected_poule]

# --- Affichage du classement actuel ---
st.markdown("### Classement actuel")
for poule in sorted(classement_initial["POULE"].unique()):
    st.subheader(f"Poule {poule}")
    classement_poule = classement_initial[classement_initial["POULE"] == poule].copy()

    if "DIF_CAL" in classement_poule.columns:
        classement_poule["DIF_CAL"] = classement_poule["DIF_CAL"].round(2)

    colonnes_completes = [
        "CLASSEMENT", "NOM_EQUIPE", "POINTS", "MJ", "DIF_CAL",
        "G", "N", "P", "PENALITES", "BP", "BC", "DIFF"
    ]
    colonnes_simplifiees = [
        "CLASSEMENT", "NOM_EQUIPE", "POINTS", "MJ", "DIF_CAL", "DIFF"
    ]
    colonnes_finales = colonnes_simplifiees if mode_simplifie else colonnes_completes
    colonnes_finales = [col for col in colonnes_finales if col in classement_poule.columns]

    classement_sorted = classement_poule.sort_values(by="DIF_CAL", ascending=False).reset_index(drop=True)
    total = len(classement_sorted)
    tiers = [total // 3, total // 3, total - 2 * (total // 3)]
    couleurs = {}

    for i in range(total):
        id_equipe = classement_sorted.loc[i, "ID_EQUIPE"]
        if i < tiers[0]:
            couleurs[id_equipe] = "#d4edda"  # vert clair
        elif i < tiers[0] + tiers[1]:
            couleurs[id_equipe] = "#fff3cd"  # jaune clair
        else:
            couleurs[id_equipe] = "#f8d7da"  # rouge clair

    def style_dif_cal(val, id_eq):
        return f"background-color: {couleurs.get(id_eq, '')};" if pd.notnull(val) else ""

    styled_df = classement_poule[colonnes_finales].style.apply(
        lambda col: [
            style_dif_cal(val, classement_poule.iloc[i]["ID_EQUIPE"])
            if col.name == "DIF_CAL" else ""
            for i, val in enumerate(col)
        ],
        axis=0
    ).format({"DIF_CAL": "{:.2f}"})

    st.dataframe(styled_df, use_container_width=True, hide_index=True)
    st.markdown(
        "*La colonne DIF_CAL évalue la difficulté du calendrier à venir. "
        "Les couleurs indiquent les tiers : vert (facile), orange (moyen), rouge (difficile).*"
    )

# --- Affichage des cas particuliers ---
if selected_poule == "Toutes les poules":
    afficher_comparatifs_speciaux(champ_id, classement_initial, date_limite)

if champ_type_classement == "PARTICULIERE" and mini_classements_initial:
    afficher_mini_classements_bloc(mini_classements_initial, "### Mini-classements des égalités particulières (Classement actuel)")


# --- Matchs à simuler ---
filtrer_non_joues = st.checkbox("Afficher uniquement les matchs non joués", value=True)

matchs_simulables = get_matchs_modifiables(champ_id, date_limite, filtrer_non_joues)

if selected_poule != "Toutes les poules":
    matchs_simulables = matchs_simulables[matchs_simulables["POULE"] == selected_poule]

st.markdown("### Matchs à simuler")

if matchs_simulables.empty:
    st.info("Aucun match disponible pour cette configuration.")
    st.stop()

# Colonnes pour affichage
colonnes_matchs_simplifiees = ["ID_MATCH", "EQUIPE_DOM", "NB_BUT_DOM", "EQUIPE_EXT", "NB_BUT_EXT"]
colonnes_matchs_completes = ["ID_MATCH", "JOURNEE", "POULE", "DATE", "EQUIPE_DOM", "NB_BUT_DOM", "EQUIPE_EXT", "NB_BUT_EXT"]

# --- Formulaire de simulation ---
if "user" not in st.session_state:
    st.info("Il est possible de modifier les scores, mais une inscription est requise pour valider la simulation.")
    st.warning("Pour s'inscrire gratuitement, utiliser le menu situé en haut à gauche de l'écran.")
    st.markdown("Sur mobile, appuyer sur l’icône `≡` pour afficher le menu.")
    
    with st.form("formulaire_simulation_locked"):
        colonnes_affichees = colonnes_matchs_simplifiees if mode_simplifie else colonnes_matchs_completes
        st.data_editor(
            matchs_simulables[colonnes_affichees],
            num_rows="dynamic",
            use_container_width=True,
            key="simulation_scores",
            column_config={
                "ID_MATCH": st.column_config.Column(disabled=True)
            }
        )
        st.form_submit_button("Valider les scores simulés", disabled=True)
    
    st.stop()

else:
    with st.form("formulaire_simulation"):
        colonnes_affichees = colonnes_matchs_simplifiees if mode_simplifie else colonnes_matchs_completes
        edited_df = st.data_editor(
            matchs_simulables[colonnes_affichees],
            num_rows="dynamic",
            use_container_width=True,
            key="simulation_scores",
            column_config={
                "ID_MATCH": st.column_config.Column(disabled=True)
            }
        )
        submit = st.form_submit_button("Valider les scores simulés")

        if submit:
            classement_simule, mini_classements_simule = recalculer_classement_simule(
                edited_df,
                champ_id,
                date_limite,
                selected_poule,
                type_classement
            )
            st.success("Simulation prise en compte.")


# --- Activation de la simulation ---
if submit:
    st.session_state.simulation_validee = True

# --- Recalcul uniquement si simulation validée ---
if st.session_state.simulation_validee:

    df_valid = edited_df.dropna(subset=["NB_BUT_DOM", "NB_BUT_EXT"]).reset_index(drop=True)

    if df_valid.empty:
        st.warning("Aucun score simulé valide.")
    else:
        st.markdown("### Matchs simulés")
        matchs_affichage = df_valid.copy()
        colonnes_affichees = colonnes_matchs_simplifiees if mode_simplifie else colonnes_matchs_completes
        st.dataframe(matchs_affichage[colonnes_affichees], use_container_width=True, hide_index=True)

        # Fusionner matchs terminés + simulables
        matchs_tous = pd.concat([matchs_termine, matchs_simulables], ignore_index=True)

        for idx, row in df_valid.iterrows():
            id_match = matchs_simulables.iloc[idx]["ID_MATCH"]
            if not pd.isna(row["NB_BUT_DOM"]) and not pd.isna(row["NB_BUT_EXT"]):
                matchs_tous.loc[matchs_tous["ID_MATCH"] == id_match, "NB_BUT_DOM"] = int(row["NB_BUT_DOM"])
                matchs_tous.loc[matchs_tous["ID_MATCH"] == id_match, "NB_BUT_EXT"] = int(row["NB_BUT_EXT"])

        matchs_tous = matchs_tous.dropna(subset=["NB_BUT_DOM", "NB_BUT_EXT"])

        # Recalcul du classement simulé
        classement_simule = get_classement_dynamique(champ_id, date_limite, matchs_override=matchs_tous)
        classement_simule = appliquer_penalites(classement_simule, date_limite)

        if champ_type_classement == "PARTICULIERE":
            classement_simule, mini_classements_simule = appliquer_diff_particuliere(classement_simule, matchs_tous)
            if selected_poule != "Toutes les poules":
                mini_classements_simule = {
                    key: mini for key, mini in mini_classements_simule.items() if key[0] == selected_poule
                }

        classement_simule = trier_et_numeroter(classement_simule, type_classement)

        ids_match_simules = matchs_simulables.iloc[df_valid.index]["ID_MATCH"].tolist()
        matchs_restants = matchs_simulables[~matchs_simulables["ID_MATCH"].isin(ids_match_simules)]

        classement_simule = calculer_difficulte_calendrier(classement_simule, matchs_restants)

        if selected_poule != "Toutes les poules":
            classement_simule = classement_simule[classement_simule["POULE"] == selected_poule]

        st.success("Simulation recalculée avec succès.")

        st.markdown("### Classement après simulation")
        for poule in sorted(classement_simule["POULE"].unique()):
            st.subheader(f"Poule {poule}")
            classement_poule = classement_simule[classement_simule["POULE"] == poule].copy()

            colonnes_completes = [
                "CLASSEMENT", "NOM_EQUIPE", "POINTS", "MJ", "DIF_CAL",
                "G", "N", "P", "PENALITES", "BP", "BC", "DIFF"
            ]
            colonnes_simplifiees = [
                "CLASSEMENT", "NOM_EQUIPE", "POINTS", "MJ", "DIF_CAL", "DIFF"
            ]
            colonnes_finales = colonnes_simplifiees if mode_simplifie else colonnes_completes
            colonnes_finales = [col for col in colonnes_finales if col in classement_poule.columns]

            if "DIF_CAL" in classement_poule.columns:
                classement_poule["DIF_CAL"] = classement_poule["DIF_CAL"].round(2)
                classement_sorted = classement_poule.sort_values(by="DIF_CAL", ascending=False).reset_index(drop=True)
                total = len(classement_sorted)
                tiers = [total // 3, total // 3, total - 2 * (total // 3)]
                couleurs = {}

                for i in range(total):
                    id_equipe = classement_sorted.loc[i, "ID_EQUIPE"]
                    if i < tiers[0]:
                        couleurs[id_equipe] = "#d4edda"
                    elif i < tiers[0] + tiers[1]:
                        couleurs[id_equipe] = "#fff3cd"
                    else:
                        couleurs[id_equipe] = "#f8d7da"

                def style_dif_cal(val, id_eq):
                    return f"background-color: {couleurs.get(id_eq, '')};" if pd.notnull(val) else ""

                styled_df = classement_poule[colonnes_finales].style.apply(
                    lambda col: [
                        style_dif_cal(val, classement_poule.iloc[i]["ID_EQUIPE"])
                        if col.name == "DIF_CAL" else ""
                        for i, val in enumerate(col)
                    ],
                    axis=0
                ).format({"DIF_CAL": "{:.2f}"})

                st.dataframe(styled_df, use_container_width=True, hide_index=True)
                st.markdown(
                    "*La colonne DIF_CAL évalue la difficulté du calendrier à venir. "
                    "Les couleurs indiquent les tiers : vert (facile), orange (moyen), rouge (difficile).*"
                )
            else:
                st.dataframe(classement_poule[colonnes_finales], use_container_width=True, hide_index=True)

        if champ_type_classement == "PARTICULIERE" and mini_classements_simule:
            afficher_mini_classements_bloc(mini_classements_simule, "### Mini-classements des égalités particulières (Simulation)")

        if selected_poule == "Toutes les poules":
            afficher_comparatifs_speciaux(champ_id, classement_simule, date_limite)



