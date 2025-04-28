import streamlit as st
from datetime import date
import simulateur_core as core

# --- Configuration de la page principale ---
st.set_page_config(page_title="Datafoot", page_icon="⚽", layout="wide", initial_sidebar_state="collapsed")

# --- Désactivation de la barre de navigation globale Streamlit (menu en haut) ---
st.markdown(
    """
    <style>
    .css-1l02zws {
        display: none;
    }
    </style>
    """, unsafe_allow_html=True)


# --- Initialiser la page courante ---
if "page" not in st.session_state:
    st.session_state.page = "home"

# --- SIDEBAR : Navigation interne ---
with st.sidebar:
    st.header("📚 Navigation")
    selection = st.radio("Sélectionner une fonctionnalité", ["Accueil", "Simulateur", "Classements"])

# --- Afficher la page sélectionnée ---
if selection == "Accueil":
    st.title("Bienvenue sur Datafoot 👋")
    # ... Afficher le contenu de la page d'accueil ici ...

elif selection == "Simulateur":
    # Naviguer vers la page Simulateur
    import pages.simulateur_whatif as simulateur_whatif
    simulateur_whatif.afficher_simulateur_whatif()

elif selection == "Classements":
    # Naviguer vers la page Classements (ex: afficher les classements actuels)
    afficher_classements_speciaux()

    
# --- PAGE D'ACCUEIL ---
if st.session_state.page == "home":
    st.title("Bienvenue sur Datafoot 👋")
    st.subheader("Présentation du projet Datafoot ⚽")

    st.markdown("""
    Datafoot est une plateforme dédiée aux championnats de football amateur. Vous pouvez consulter les classements officiels, simuler les résultats des matchs à venir, et analyser les différences particulières entre les équipes.

    Fonctionnalités principales :
    - **Simulations de résultats** : Projetez différents scénarios pour voir l'impact sur le classement.
    - **Règles spéciales** : Consulter les classements spéciaux pour les catégories comme U19, U17, N2, N3.
    - **Différences particulières** : Gérez les égalités dans les classements avec des critères alternatifs comme les confrontations directes.

    🔒 Connectez-vous pour commencer.
    """)

    # --- Fonctionnalités à venir (explications) ---
    st.markdown("### Fonctionnalités principales :")
    st.markdown("""
    1. **Simulations de résultats** : Vous pouvez simuler des résultats pour les matchs à venir et voir l'impact sur le classement global.
    2. **Règles spéciales** : Accédez à des classements spécifiques (ex : U19, U17, N2, N3) pour des analyses détaillées.
    3. **Différences particulières** : Gérez les égalités entre équipes avec des critères comme les confrontations directes.
    """)

    # --- Option de navigation vers simulateur ---
    st.markdown("---")
    st.markdown("### Que souhaitez-vous faire ?")
    
    if st.button("🎯 Accéder au simulateur"):
        st.session_state.page = "simulation"
    
    # --- Lien vers la documentation ou aide
    st.markdown("### Aide et Documentation")
    st.markdown("Pour en savoir plus, consultez notre [guide d'utilisation](#) ou contactez-nous à [support@datafoot.fr](mailto:support@datafoot.fr).")

# --- Navigation principale ---
elif st.session_state.page == "simulation":
    afficher_classements_speciaux()

