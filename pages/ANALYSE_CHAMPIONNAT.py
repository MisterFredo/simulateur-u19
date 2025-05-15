import streamlit as st
import pandas as pd
from datetime import date
from google.cloud import bigquery
from google.oauth2 import service_account

import sys
import os
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
    recalculer_classement_simule,
    enregistrer_inscription
)

# --- CONFIG STREAMLIT
st.set_page_config(page_title="SIMULATEUR - Datafoot", layout="wide")

# --- FONCTION AFFICHAGE COMPARATIFS SPÉCIAUX
def afficher_comparatifs_speciaux(champ_id, classement_df, date_limite):
    if champ_id == 6:
        st.markdown("### Règle spéciale U19 NAT : pts obtenus par les équipes classées 11ème vs celles classées de 6 à 10")
        df_11e = classement_special_u19(classement_df, champ_id, date_limite=date_limite, journee_min=journee_min, journee_max=journee_max)
        if df_11e is not None:
            st.dataframe(df_11e, use_container_width=True, hide_index=True)

    if champ_id == 7:
        st.markdown("### Règle spéciale U17 NAT : pts obtenus par les équipes classées 2ème vs celles classées de 1 à 6")
        df_2e = classement_special_u17(classement_df, champ_id, date_limite=date_limite, journee_min=journee_min, journee_max=journee_max)
        if df_2e is not None:
            st.dataframe(df_2e, use_container_width=True, hide_index=True)

    # --- Bloc désactivé temporairement : Comparatif spécial N2 ---
    # if champ_id == 4:
    #     st.markdown("### Règle spéciale N2")
    #     df_13e = classement_special_n2(classement_df, champ_id, date_limite)
    #     if df_13e is not None:
    #         st.dataframe(df_13e, use_container_width=True, hide_index=True)

    if champ_id == 5:
        st.markdown("### Règle spéciale N3 : pts obtenus par les équipes classées 10ème vs celles classées de 5 à 9")
        df_10e = classement_special_n3(classement_df, champ_id, date_limite)
        if df_10e is not None:
            st.dataframe(df_10e, use_container_width=True, hide_index=True)


# --- FACTORISATION MINI-CLASSEMENTS
def afficher_mini_classements_bloc(mini_classements, titre_bloc):
    st.markdown(titre_bloc)
    
    for (poule, pts), mini in mini_classements.items():
        # Appliquer le filtre de poule sélectionnée
        if selected_poule != "Toutes les poules" and poule != selected_poule:
            continue  # on saute cette poule si elle ne correspond pas

        with st.expander(f"Poule {poule} – Égalité à {pts} points", expanded=True):
            st.markdown("**Mini-classement / Mini-Rankings :**")
            df_mini = mini["classement"].copy()
            colonnes_mini = [col for col in df_mini.columns if col != "CLASSEMENT"]
            st.dataframe(df_mini[colonnes_mini], use_container_width=True, hide_index=True)

            st.markdown("**Matchs concernés / Affected Matches :**")
            df_matchs = mini["matchs"].copy()
            st.dataframe(df_matchs.reset_index(drop=True), use_container_width=True, hide_index=True)

# --- INIT SESSION STATE
if "simulation_validee" not in st.session_state:
    st.session_state.simulation_validee = False

# --- Chargement championnats
championnats_df = load_championnats()

from datetime import date

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

# --- Connexion / Inscription Utilisateur ---
st.sidebar.markdown("---")

if "user" in st.session_state:
    st.sidebar.success(f"Connecté : {st.session_state['user_name']}")
else:
    st.sidebar.subheader("Submit")
    user_name = st.sidebar.text_input("Nom / Name")
    user_email = st.sidebar.text_input("Email")

    if st.sidebar.button("Submit", key="btn_connexion_sidebar"):
        if user_name and user_email:
            st.session_state.user_name = user_name
            st.session_state.user_email = user_email
            st.session_state["user"] = user_email
            st.session_state.page = "home"
            st.sidebar.success("Connexion réussie.")
        else:
            st.sidebar.warning("Renseigner le nom et l'email / Please fill in Name and email")

    st.sidebar.markdown("---")
    st.sidebar.subheader("Créer un compte / Create an Account")

    with st.sidebar.form("form_inscription"):
        prenom = st.text_input("Prénom / First Name")
        nom = st.text_input("Nom / Name")
        email_inscription = st.text_input("Email")
        club = st.text_input("Club / Company")

        st.markdown("Neswsletter DATAFOOT.AI : analyses & insights")
        newsletter = st.checkbox("S'abonner / Subscribe")

        submitted = st.form_submit_button("Créer un compte / Create an Account")

        if submitted:
            if prenom and nom and email_inscription:
                st.session_state["user"] = email_inscription
                st.session_state["user_name"] = f"{prenom} {nom}"
                st.session_state["user_email"] = email_inscription
                st.session_state["club"] = club
                st.session_state["newsletter"] = "oui" if newsletter else "non"

                enregistrer_inscription(
                    email=email_inscription,
                    prenom=prenom,
                    nom=nom,
                    societe_club=club,
                    newsletter="oui" if newsletter else "non",
                    source="simulateur"
                )

                st.sidebar.success("Compte activé.")
            else:
                st.sidebar.warning("Remplir tous les champs obligatoires / Please fill in all the mandatories fields")


# --- TITRE
st.title(f"Simulation – {selected_nom}")

# --- Choix Mode Simplifié
mode_simplifie = st.toggle("Afficher en mode simplifié (mobile friendly)", value=True)

colonnes_completes = ["CLASSEMENT", "NOM_EQUIPE", "POINTS", "PENALITES", "MJ", "G", "N", "P", "BP", "BC", "DIFF"]
colonnes_simplifiees = ["CLASSEMENT", "NOM_EQUIPE", "POINTS", "DIFF", "MJ"]

# --- 1. CLASSEMENT ACTUEL

# Chargement des infos championnat
championnats = load_championnats()
championnat_info = championnats[championnats["ID_CHAMPIONNAT"] == champ_id].iloc[0]

# Initialisation des variables
date_limite = None
journee_min = None
journee_max = None

# Sélection du mode de filtrage
if pd.notnull(championnat_info["NBRE_JOURNEES"]):
    mode_filtrage = st.radio(
        "Mode de calcul du classement / Ranking filter mode",
        ["Par date", "Par journée"],
        index=0,
        horizontal=True
    )

    if mode_filtrage == "Par date":
        date_limite = st.date_input("📅 Date limite / Cut-off date", value=date.today())
        journee_min = None
        journee_max = None
    else:
        max_journee = int(championnat_info["NBRE_JOURNEES"])
        st.markdown("### 📆 Plage de journées / Matchday range")
        col1, col2 = st.columns(2)

        with col1:
            journee_min = st.number_input(
                "Journée de début / Start matchday",
                min_value=1,
                max_value=max_journee,
                value=1,
                key="journee_min"
            )
        with col2:
            journee_max = st.number_input(
                "Journée de fin / End matchday",
                min_value=journee_min,
                max_value=max_journee,
                value=max_journee,
                key="journee_max"
            )
        date_limite = None
else:
    st.markdown("ℹ️ Ce championnat ne permet le calcul que par **date** (non structuré en journées).")
    date_limite = st.date_input("📅 Date limite / Cut-off date", value=date.today())
    journee_min = None
    journee_max = None


# Récupération des matchs terminés et restants
matchs_termine = get_matchs_termine(
    champ_id,
    date_limite=date_limite,
    journee_min=journee_min,
    journee_max=journee_max
)
matchs_restants = get_matchs_modifiables(champ_id, date_limite=date_limite, non_joues_only=True)

# Calcul du classement initial
classement_initial = get_classement_dynamique(
    champ_id,
    date_limite=date_limite,
    journee_min=journee_min,
    journee_max=journee_max,
    matchs_override=matchs_termine
)

# Cas des égalités particulières
if champ_type_classement == "PARTICULIERE":
    classement_initial, mini_classements_initial = appliquer_diff_particuliere(classement_initial, matchs_termine)

# Tri et post-traitements
classement_initial = trier_et_numeroter(classement_initial, type_classement)
classement_initial = calculer_difficulte_calendrier(classement_initial, matchs_restants)

if selected_poule != "Toutes les poules":
    classement_initial = classement_initial[classement_initial["POULE"] == selected_poule]

# --- Affichage du classement actuel
# Titre dynamique du classement
if journee_min is not None and journee_max is not None:
    if journee_min == journee_max:
        titre_classement = f"### 📊 Classement après la J{journee_max}"
    else:
        titre_classement = f"### 📊 Classement de la J{journee_min} à la J{journee_max}"
elif date_limite:
    titre_classement = f"### 📊 Classement au {date_limite.strftime('%d/%m/%Y')}"
else:
    titre_classement = "### 📊 Classement actuel"
    
st.markdown("### Classement actuel / Current Ranking")
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
            couleurs[id_equipe] = "#c6f6d5"  # vert pastel
        elif i < tiers[0] + tiers[1]:
            couleurs[id_equipe] = "#fefcbf"  # orange-jaune pastel
        else:
            couleurs[id_equipe] = "#fed7d7"  # rouge pastel

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
    st.markdown("*La colonne DIF_CAL évalue la difficulté du calendrier à venir / The DIF_CAL column shows upcoming schedule difficulty : 🟩 vert (easy), 🟧 orange (medium), 🟥 rouge (hard).*")

if selected_poule == "Toutes les poules":
    afficher_comparatifs_speciaux(champ_id, classement_initial, date_limite)

if champ_type_classement == "PARTICULIERE" and mini_classements_initial:
    afficher_mini_classements_bloc(mini_classements_initial, "### Mini-classements des égalités particulières (Classement actuel)")

# --- 2BIS. DATE DE SIMULATION
st.markdown("### 🕓 Date de simulation / Simulation date")
date_limite = st.date_input("📅 Choisissez une date pour simuler les matchs", value=date(2025, 6, 30))

# --- 3. MATCHS À SIMULER

filtrer_non_joues = st.checkbox("Afficher uniquement les matchs non joués / Show only unplayed matches", value=True)

matchs_simulables = get_matchs_modifiables(champ_id, date_limite, non_joues_only=filtrer_non_joues)

if selected_poule != "Toutes les poules / Every groups":
    matchs_simulables = matchs_simulables[matchs_simulables["POULE"] == selected_poule]

st.markdown("### Matchs à simuler / Matchs to simulate")

if matchs_simulables.empty:
    st.info("Aucun match disponible pour cette configuration. / No game available")
    st.stop()

# Colonnes pour l'affichage mobile-friendly
colonnes_matchs_simplifiees = ["EQUIPE_DOM", "NB_BUT_DOM", "EQUIPE_EXT", "NB_BUT_EXT"]
colonnes_matchs_completes = ["JOURNEE", "POULE", "DATE", "EQUIPE_DOM", "NB_BUT_DOM", "EQUIPE_EXT", "NB_BUT_EXT"]

# --- 3BIS. FORMULAIRE DE SIMULATION ---
if "user" not in st.session_state:
    st.warning("Créez votre compte depuis le menu latéral pour activer le simulateur. / Create account from the sidebar to activate the simulator.")
    
    with st.form("formulaire_simulation_locked"):
        colonnes_affichees = colonnes_matchs_simplifiees if mode_simplifie else colonnes_matchs_completes

        st.data_editor(
            matchs_simulables[colonnes_affichees],
            num_rows="dynamic",
            use_container_width=True,
            key="simulation_scores"
        )
        st.form_submit_button("🔁 Submit", disabled=True)
    
    st.stop()

else:
    with st.form("formulaire_simulation"):
        colonnes_affichees = colonnes_matchs_simplifiees if mode_simplifie else colonnes_matchs_completes

        edited_df = st.data_editor(
            matchs_simulables[colonnes_affichees],
            num_rows="dynamic",
            use_container_width=True,
            key="simulation_scores"
        )

        # Réintégrer ID_MATCH pour le traitement
        edited_df["ID_MATCH"] = matchs_simulables["ID_MATCH"].values

        submit = st.form_submit_button("🔁 Submit")

        if submit:
            classement_simule, mini_classements_simule = recalculer_classement_simule(
                edited_df,
                champ_id,
                date_limite,
                selected_poule,
                type_classement
            )

            st.success("✅ Simulation")


# --- 4. ACTIVATION SIMULATION
if submit:
    st.session_state.simulation_validee = True

# --- 5. SIMULATION SEULEMENT SI VALIDATION
if st.session_state.simulation_validee:

    df_valid = edited_df.dropna(subset=["NB_BUT_DOM", "NB_BUT_EXT"]).reset_index(drop=True)

    if df_valid.empty:
        st.warning("🚫 Aucun score simulé valide / No valid simulated score.")
    else:
        st.markdown("### Matchs simulés / Simulated Matchs")
        matchs_affichage = df_valid.copy()
        colonnes_affichees = colonnes_matchs_simplifiees if mode_simplifie else colonnes_matchs_completes
        st.dataframe(matchs_affichage[colonnes_affichees], use_container_width=True, hide_index=True)

        # Fusionner matchs terminés + matchs simulables
        matchs_tous = pd.concat([matchs_termine, matchs_simulables], ignore_index=True)

        # Appliquer les scores simulés
        for idx, row in df_valid.iterrows():
            id_match = row["ID_MATCH"]
            if not pd.isna(row["NB_BUT_DOM"]) and not pd.isna(row["NB_BUT_EXT"]):
                matchs_tous.loc[matchs_tous["ID_MATCH"] == id_match, "NB_BUT_DOM"] = int(row["NB_BUT_DOM"])
                matchs_tous.loc[matchs_tous["ID_MATCH"] == id_match, "NB_BUT_EXT"] = int(row["NB_BUT_EXT"])

        matchs_tous = matchs_tous.dropna(subset=["NB_BUT_DOM", "NB_BUT_EXT"])

        # Recalcul du classement
        classement_simule = get_classement_dynamique(champ_id, date_limite, matchs_override=matchs_tous)
        classement_simule = appliquer_penalites(classement_simule, date_limite)

        # Appliquer égalités particulières
        if champ_type_classement == "PARTICULIERE":
            classement_simule, mini_classements_simule = appliquer_diff_particuliere(classement_simule, matchs_tous)
            if selected_poule != "Toutes les poules":
                mini_classements_simule = {
                    key: mini for key, mini in mini_classements_simule.items() if key[0] == selected_poule
                }

        classement_simule = trier_et_numeroter(classement_simule, type_classement)

        # Identifier les matchs restants non simulés
        ids_match_simules = matchs_simulables.iloc[df_valid.index]["ID_MATCH"].tolist()
        matchs_restants = matchs_simulables[~matchs_simulables["ID_MATCH"].isin(ids_match_simules)]

        # Calcul DIF_CAL
        classement_simule = calculer_difficulte_calendrier(classement_simule, matchs_restants)

        if selected_poule != "Toutes les poules":
            classement_simule = classement_simule[classement_simule["POULE"] == selected_poule]

        st.success("✅ Simulation")

        st.markdown("### Nouveau Classement simulé / New Ranking")
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

            # Arrondi + couleurs DIF_CAL
            if "DIF_CAL" in classement_poule.columns:
                classement_poule["DIF_CAL"] = classement_poule["DIF_CAL"].round(2)
                classement_sorted = classement_poule.sort_values(by="DIF_CAL", ascending=False).reset_index(drop=True)
                total = len(classement_sorted)
                tiers = [total // 3, total // 3, total - 2 * (total // 3)]
                couleurs = {}

                for i in range(total):
                    id_equipe = classement_sorted.loc[i, "ID_EQUIPE"]
                    if i < tiers[0]:
                        couleurs[id_equipe] = "#c6f6d5"  # vert pastel (🟩)
                    elif i < tiers[0] + tiers[1]:
                        couleurs[id_equipe] = "#fefcbf"  # orange-jaune pastel (🟧)
                    else:
                        couleurs[id_equipe] = "#fed7d7"  # rouge pastel (🟥)

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
                st.markdown("*La colonne DIF_CAL évalue la difficulté du calendrier à venir / The DIF_CAL column shows upcoming schedule difficulty : 🟩 vert (easy), 🟧 orange (medium), 🟥 rouge (hard).*")
                st.dataframe(classement_poule[colonnes_finales], use_container_width=True, hide_index=True)

        if champ_type_classement == "PARTICULIERE" and mini_classements_simule:
            afficher_mini_classements_bloc(mini_classements_simule, "### Mini-classements des égalités particulières (Simulation)")

        if selected_poule == "Toutes les poules":
            afficher_comparatifs_speciaux(champ_id, classement_simule, date_limite)



