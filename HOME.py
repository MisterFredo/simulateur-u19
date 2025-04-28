import streamlit as st
from datetime import date
import simulateur_core as core

# --- Configuration de la page principale ---
st.set_page_config(page_title="Datafoot.ai", page_icon="🏆", layout="wide")

with st.sidebar:
    st.image("LOGO DATAFOOT CARRE.png", use_container_width=True)

    # --- Petit style visuel ---
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] {
            background-color: #f9f9f9;
        }
        [data-testid="stSidebar"] img {
            margin-bottom: 10px;
        }
        hr {
            margin-top: 0px;
            margin-bottom: 10px;
            border: none;
            height: 1px;
            background-color: #ddd;
        }
        </style>
        <hr>
        """,
        unsafe_allow_html=True,
    )

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
    if st.button("🎯 Accéder au simulateur"):
        st.session_state.page = "simulation"
    
    # --- Lien vers la documentation ou aide
    st.markdown("### Aide et Documentation")
    st.markdown("Pour en savoir plus, consultez notre [guide d'utilisation](#) ou contactez-nous à [support@datafoot.fr](mailto:support@datafoot.fr).")

# --- PAGE SIMULATEUR ---
elif selection == "Simulateur":
    # Appeler la fonction qui gère la simulation, par exemple
    import pages.ANALYSE_CHAMPIONNAT as analyse_championnat
    analyse_championnat.afficher_ANALYSE_CHAMPIONNAT()


# --- PAGE CLASSEMENTS ---
elif selection == "Classements":
    # Appeler la fonction qui gère l'affichage des classements
    afficher_classements_speciaux()
