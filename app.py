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
        st.session_state.selected_id_championnat = 3  # NATIONAL

    if st.button("🏆 National 2 (3 Poules)"):
        st.session_state.page = "championnat"
        st.session_state.selected_id_championnat = 4  # NATIONAL 2

    if st.button("🏆 National 3 (10 Poules)"):
        st.session_state.page = "championnat"
        st.session_state.selected_id_championnat = 5  # NATIONAL 3

    st.markdown("**Jeunes Nationaux**")
    if st.button("🎯 19 NAT"):
        st.session_state.page = "championnat"
        st.session_state.selected_id_championnat = 6  # 19 NAT

    if st.button("🎯 17 NAT"):
        st.session_state.page = "championnat"
        st.session_state.selected_id_championnat = 7  # 17 NAT

    st.markdown("**Jeunes Régionaux**")
    if st.button("🧢 18 R1 HDF"):
        st.session_state.page = "championnat"
        st.session_state.selected_id_championnat = 27  # 18 R1 HDF

    if st.button("🧢 18 R1 IDF"):
        st.session_state.page = "championnat"
        st.session_state.selected_id_championnat = 32  # 18 R1 IDF

    if st.button("🧢 17 R1 HDF"):
        st.session_state.page = "championnat"
        st.session_state.selected_id_championnat = 35  # 17 R1 HDF


def afficher_simulateur():
    import simulateur_core

    st.title("Classements Officiels ⚽")

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

    selected_nom = st.selectbox("Sélectionnez un championnat :", list(championnats_dict.keys()))

    if selected_nom:
        selected_id = championnats_dict[selected_nom]

        import simulateur
        simulateur.afficher_classement(selected_id)

    # --- Retour à l'accueil ---
    st.markdown("---")
    if st.button("⬅️ Retour à l'accueil"):
        st.session_state.page = "home"
        
def afficher_classements_speciaux():
    st.title("Simulations de Classements 🔮")

    import pages.simulateur_whatif as simulateur_whatif
    simulateur_whatif.afficher_simulateur_whatif()

    # --- Retour à l'accueil ---
    st.markdown("---")
    if st.button("⬅️ Retour à l'accueil"):
        st.session_state.page = "home"

def afficher_championnat():
    if "selected_id_championnat" in st.session_state:
        id_championnat = st.session_state.selected_id_championnat

        from datetime import date
        date_limite = date.today().isoformat()

        st.title(f"🏆 Championnat ID {id_championnat}")
        st.info(f"Chargement du classement pour championnat ID {id_championnat} (à la date {date_limite})...")

        import simulateur_core as core

        # --- Chargement des matchs terminés ---
        matchs = core.get_matchs_termine(id_championnat, date_limite)

        # --- Calcul du classement dynamique ---
        classement = core.get_classement_dynamique(id_championnat, date_limite)

        if classement is None or classement.empty:
            st.warning("Aucun match trouvé pour ce championnat.")
        else:
            classement = core.appliquer_penalites(classement, date_limite)
            classement, _ = core.appliquer_diff_particuliere(classement, matchs)
            type_classement = core.get_type_classement(id_championnat)
            classement = core.trier_et_numeroter(classement, type_classement)

            st.markdown("### Classement actuel 📊")
            st.dataframe(classement, use_container_width=True)

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

