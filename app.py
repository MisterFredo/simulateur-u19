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
            st.rerun()

    with col2:
        if st.button("🔮 Lancer une Simulation"):
            st.session_state.page = "simulation"
            st.rerun()

    st.markdown("---")
    st.subheader("⚡ Accès rapides aux championnats")

    st.markdown("**Séniors**")
    if st.button("🏆 National"):
        st.session_state.page = "championnat"
        st.session_state.selected_id_championnat = 3
        st.rerun()

    if st.button("🏆 National 2 (3 Poules)"):
        st.session_state.page = "championnat"
        st.session_state.selected_id_championnat = 4
        st.rerun()

    if st.button("🏆 National 3 (10 Poules)"):
        st.session_state.page = "championnat"
        st.session_state.selected_id_championnat = 5
        st.rerun()

    st.markdown("**Jeunes Nationaux**")
    if st.button("🎯 U19 National"):
        st.session_state.page = "championnat"
        st.session_state.selected_id_championnat = 6
        st.rerun()

    if st.button("🎯 U17 National"):
        st.session_state.page = "championnat"
        st.session_state.selected_id_championnat = 7
        st.rerun()

    st.markdown("**Jeunes Régionaux**")
    if st.button("🧢 U17 R1 HDF"):
        st.session_state.page = "championnat"
        st.session_state.selected_id_championnat = 35
        st.rerun()

    if st.button("🧢 U18 R1 HDF"):
        st.session_state.page = "championnat"
        st.session_state.selected_id_championnat = 27
        st.rerun()

    if st.button("🧢 U18 R1 IDF"):
        st.session_state.page = "championnat"
        st.session_state.selected_id_championnat = 32
        st.rerun()

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

        import simulateur_core as core

        championnats = core.load_championnats()
        selected_row = championnats[championnats['ID_CHAMPIONNAT'] == id_championnat]

        if not selected_row.empty:
            nom_championnat = selected_row['NOM_CHAMPIONNAT'].values[0]
        else:
            nom_championnat = f"ID {id_championnat}"

        st.title(f"🏆 {nom_championnat}")
        st.info(f"Chargement du classement pour {nom_championnat} (à la date {date_limite})...")

        matchs = core.get_matchs_termine(id_championnat, date_limite)
        classement = core.get_classement_dynamique(id_championnat, date_limite)

        if classement is None or classement.empty:
            st.warning("Aucun match trouvé pour ce championnat.")
        else:
            classement = core.appliquer_penalites(classement, date_limite)
            classement, _ = core.appliquer_diff_particuliere(classement, matchs)
            type_classement = core.get_type_classement(id_championnat)
            classement = core.trier_et_numeroter(classement, type_classement)

            poules_dispo = classement['POULE'].unique()

            for poule in sorted(poules_dispo):
                st.markdown(f"### Poule {poule}")

                classement_poule = classement[classement["POULE"] == poule]

                colonnes_souhaitées = [
                    "CLASSEMENT", "NOM_EQUIPE", "POINTS",
                    "PENALITES", "G", "N", "P", "BP", "BC", "DIFF"
                ]
                colonnes_finales = [col for col in colonnes_souhaitées if col in classement_poule.columns]
                classement_poule = classement_poule[colonnes_finales]

                st.dataframe(classement_poule, use_container_width=True)

        st.markdown("---")
        if st.button("⬅️ Retour à l'accueil"):
            st.session_state.page = "home"

    else:
        st.error("Aucun championnat sélectionné. Retour à l'accueil.")
        if st.button("⬅️ Retour à l'accueil"):
            st.session_state.page = "home"
            st.experimental_rerun()


# --- Bloc navigation principale ---
if st.session_state.page == "home":
    afficher_accueil()

elif st.session_state.page == "classement":
    afficher_simulateur()

elif st.session_state.page == "simulation":
    afficher_classements_speciaux()

elif st.session_state.page == "championnat":
    afficher_championnat()

