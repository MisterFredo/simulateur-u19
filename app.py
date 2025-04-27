import streamlit as st
from datetime import date
import simulateur_core as core

# --- Définir la configuration de la page principale ---
st.set_page_config(page_title="Datafoot", page_icon="⚽", layout="wide")

# --- Initialiser la page courante ---
if "page" not in st.session_state:
    st.session_state.page = "home"

# --- Chargement des championnats disponibles ---
championnats_df = core.load_championnats()
championnats_list = championnats_df['NOM_CHAMPIONNAT'].tolist()

# --- SIDEBAR NAVIGATION ---
with st.sidebar:
    st.header("📚 Navigation")

    selected_championnat_sidebar = st.selectbox("Choisissez un championnat", options=championnats_list)
    selected_date_sidebar = st.date_input("Sélectionnez la date limite", value=date.today())

    if st.button("🔎 Afficher ce championnat"):
        if selected_championnat_sidebar:
            selected_row = championnats_df[championnats_df['NOM_CHAMPIONNAT'] == selected_championnat_sidebar]
            if not selected_row.empty:
                id_championnat_sidebar = selected_row['ID_CHAMPIONNAT'].values[0]
                st.session_state.selected_id_championnat = id_championnat_sidebar
                st.session_state.selected_date_limite = selected_date_sidebar.isoformat()
                st.session_state.page = "championnat"
                st.experimental_rerun()

# --- PAGE PRINCIPALE ---
if st.session_state.page == "home":
    st.title("Bienvenue sur Datafoot 👋")
    st.subheader("Accès rapides aux championnats 📈")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🏆 National"):
            st.session_state.selected_id_championnat = 3
            st.session_state.selected_date_limite = date.today().isoformat()
            st.session_state.page = "championnat"
            st.experimental_rerun()

        if st.button("🏆 National 2"):
            st.session_state.selected_id_championnat = 4
            st.session_state.selected_date_limite = date.today().isoformat()
            st.session_state.page = "championnat"
            st.experimental_rerun()

        if st.button("🏆 National 3"):
            st.session_state.selected_id_championnat = 5
            st.session_state.selected_date_limite = date.today().isoformat()
            st.session_state.page = "championnat"
            st.experimental_rerun()

    with col2:
        if st.button("🎯 U19 National"):
            st.session_state.selected_id_championnat = 6
            st.session_state.selected_date_limite = date.today().isoformat()
            st.session_state.page = "championnat"
            st.experimental_rerun()

        if st.button("🎯 U17 National"):
            st.session_state.selected_id_championnat = 7
            st.session_state.selected_date_limite = date.today().isoformat()
            st.session_state.page = "championnat"
            st.experimental_rerun()

        if st.button("🧢 18 R1 HDF"):
            st.session_state.selected_id_championnat = 27
            st.session_state.selected_date_limite = date.today().isoformat()
            st.session_state.page = "championnat"
            st.experimental_rerun()

        if st.button("🧢 18 R1 IDF"):
            st.session_state.selected_id_championnat = 32
            st.session_state.selected_date_limite = date.today().isoformat()
            st.session_state.page = "championnat"
            st.experimental_rerun()

        if st.button("🧢 17 R1 HDF"):
            st.session_state.selected_id_championnat = 35
            st.session_state.selected_date_limite = date.today().isoformat()
            st.session_state.page = "championnat"
            st.experimental_rerun()

# --- AFFICHAGE CHAMPIONNAT ---
if st.session_state.page == "championnat":
    if "selected_id_championnat" in st.session_state and "selected_date_limite" in st.session_state:
        from simulateur import afficher_classement
        afficher_classement(
            st.session_state.selected_id_championnat,
            st.session_state.selected_date_limite
        )
    else:
        st.error("Aucun championnat sélectionné.")


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

# --- Navigation principale ---
if st.session_state.page == "home":
    st.title("Bienvenue sur Datafoot 👋")
    st.subheader("Accès rapides aux championnats 📈")
    # >>> ici on ne remet PAS les boutons, ils sont déjà en haut

elif st.session_state.page == "classement":
    afficher_simulateur()

elif st.session_state.page == "simulation":
    afficher_classements_speciaux()

elif st.session_state.page == "championnat":
    if "selected_id_championnat" in st.session_state:
        afficher_championnat()
    else:
        st.error("Aucun championnat sélectionné.")

