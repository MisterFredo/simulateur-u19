import streamlit as st

# --- Définir la configuration de la page principale ---
st.set_page_config(page_title="Datafoot", page_icon="⚽", layout="centered")

# --- Initialiser la page courante ---
if "page" not in st.session_state:
    st.session_state.page = "home"

# --- Fonctions pour afficher les différentes sections ---
def afficher_accueil():
    st.title("Bienvenue sur Datafoot 👋")
    
    st.markdown("### Que souhaitez-vous faire ?")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("📊 Voir Classement Officiel"):
            st.session_state.page = "classement"

    with col2:
        if st.button("🔮 Lancer une Simulation"):
            st.session_state.page = "simulation"

    st.markdown("---")
    st.subheader("⚡ Accès rapides aux championnats")

    st.markdown("**Séniors**")
    if st.button("🏆 National"):
        st.session_state.page = "championnat"
        st.session_state.selected_championnat = "National"

    if st.button("🏆 National 2 (3 Poules)"):
        st.session_state.page = "championnat"
        st.session_state.selected_championnat = "National 2"

    if st.button("🏆 National 3 (10 Poules)"):
        st.session_state.page = "championnat"
        st.session_state.selected_championnat = "National 3"

    st.markdown("**Jeunes Nationaux**")
    if st.button("🎯 U19 National"):
        st.session_state.page = "championnat"
        st.session_state.selected_championnat = "U19 National"

    if st.button("🎯 U17 National"):
        st.session_state.page = "championnat"
        st.session_state.selected_championnat = "U17 National"

    st.markdown("**Jeunes Régionaux**")
    if st.button("🧢 U17 R1"):
        st.session_state.page = "championnat"
        st.session_state.selected_championnat = "U17 R1"

    if st.button("🧢 U18 R1"):
        st.session_state.page = "championnat"
        st.session_state.selected_championnat = "U18 R1"

def afficher_simulateur():
    import simulateur
    import simulateur_core

    st.title("Classements Officiels ⚽")

    # --- Dictionnaire de tes championnats officiels ---
    championnats_dict = {
        "🏆 National": 3,
        "🏆 National 2": 4,
        "🏆 National 3": 5,
        "🎯 19 NAT": 6,
        "🎯 17 NAT": 7,
        "🧢 18 R1 HDF": 27,
        "🧢 18 R1 IDF": 32,
        "🧢 17 R1 HDF": 35,
    }

    # --- Sélection du championnat ---
    selected_nom = st.selectbox("Sélectionnez un championnat :", list(championnats_dict.keys()))

    if selected_nom:
        selected_id = championnats_dict[selected_nom]
        simulateur.afficher_classement(selected_id)

def afficher_classements_speciaux():
    # >>> Ici tu vas appeler la logique de simulateur_whatif.py <<<
    import pages.simulateur_whatif as simulateur_whatif
    simulateur_whatif.afficher_simulateur_whatif()  # Ou la fonction principale que tu veux utiliser

def afficher_championnat():
    if "selected_championnat" in st.session_state:
        championnat = st.session_state.selected_championnat
        st.title(f"🏆 Championnat : {championnat}")
        st.info(f"Chargement des données pour {championnat}...")

        # --- Charger et afficher un premier classement réel ---
        import simulateur_core as core
        championnats = core.load_championnats()
        selected_row = championnats[championnats['NOM_CHAMPIONNAT'] == championnat]

        if not selected_row.empty:
            id_championnat = selected_row['ID_CHAMPIONNAT'].values[0]

            matchs = core.get_matchs_termine(id_championnat)
            classement = core.get_classement_dynamique(matchs)
            classement = core.appliquer_penalites(classement)
            classement = core.appliquer_diff_particuliere(classement)
            classement = core.trier_et_numeroter(classement)

            st.markdown("### Classement actuel 📊")
            st.dataframe(classement, use_container_width=True)
        else:
            st.warning("Championnat introuvable.")

        # --- Retour à l'accueil ---
        st.markdown("---")
        if st.button("⬅️ Retour à l'accueil"):
            st.session_state.page = "home"

    else:
        st.error("Aucun championnat sélectionné. Retour à l'accueil.")
        if st.button("⬅️ Retour à l'accueil"):
            st.session_state.page = "home"


# --- Bloc navigation principale ---
if st.session_state.page == "home":
    afficher_accueil()

elif st.session_state.page == "classement":
    afficher_simulateur()

elif st.session_state.page == "simulation":
    afficher_classements_speciaux()

elif st.session_state.page == "championnat":
    afficher_championnat()

