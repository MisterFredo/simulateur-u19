import streamlit as st
from datetime import date
import simulateur_core as core

# --- Configuration de la page principale (titre de page HOME) ---
st.set_page_config(page_title="Datafoot - Accueil", page_icon="⚽", layout="wide")

# --- Initialiser la page courante ---
if "page" not in st.session_state:
    st.session_state.page = "home"

# --- SIDEBAR : Identification ---
with st.sidebar:
    st.header("📚 Identification")
    user_name = st.text_input("Nom de l'utilisateur")
    user_email = st.text_input("Email")
    if st.button("Se connecter"):
        if user_name and user_email:
            st.session_state.user_name = user_name
            st.session_state.user_email = user_email
            st.session_state.page = "home"  # Revenir à "home" après connexion
        else:
            st.warning("Veuillez entrer votre nom et email.")

    # --- Menu de navigation : METTRE À JOUR ICI ---
    # Utilisation d'un selectbox pour la navigation
    selection = st.selectbox("Naviguer", ["Accueil", "Simulateur", "Classements"])

# --- PAGE D'ACCUEIL ---
if selection == "Accueil":
    st.title("Bienvenue sur Datafoot 👋")
    st.subheader("Présentation du projet Datafoot ⚽")
    # Affichage des informations sur Datafoot ici...
    
    # --- Option de navigation vers simulateur ---
    if st.button("🎯 Accéder au simulateur"):
        st.session_state.page = "simulation"

# --- PAGE SIMULATEUR ---
elif selection == "Simulateur":
    # Appeler la fonction qui gère la simulation, par exemple
    import pages.simulateur_whatif as simulateur_whatif
    simulateur_whatif.afficher_simulateur_whatif()

# --- PAGE CLASSEMENTS ---
elif selection == "Classements":
    # Appeler la fonction qui gère l'affichage des classements
    afficher_classements_speciaux()
