import streamlit as st
from datetime import date
import simulateur_core as core

# --- Configuration de la page principale ---
st.set_page_config(page_title="Datafoot.ai", page_icon="🏆", layout="wide")

with st.sidebar:
    st.image("LOGO DATAFOOT CARRE.png", use_container_width=True)

    # --- Style moderne sidebar ---
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] {
            background-color: #f0f2f6;
            padding: 1rem;
            border-right: 1px solid #e6e6e6;
        }
        [data-testid="stSidebar"] img {
            margin-bottom: 1rem;
            border-radius: 12px;
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
        }
        hr {
            margin-top: 0.5rem;
            margin-bottom: 1rem;
            border: none;
            height: 2px;
            background: linear-gradient(to right, #ddd, #fff);
        }
        </style>
        <hr>
        """,
        unsafe_allow_html=True,
    )

# --- Style moderne du contenu principal ---
st.markdown(
    """
    <style>
    [data-testid="stAppViewContainer"] {
        background-color: #ffffff;
        padding: 2rem 2rem 2rem 2rem;
    }
    h1, h2, h3 {
        color: #333333;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
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
        color: #ffffff;
    }
    </style>
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

# Bouton sobre pour accéder au simulateur
st.markdown("""
<style>
.button-simulateur {
    display: inline-block;
    padding: 0.8rem 1.5rem;
    font-size: 1.1rem;
    font-weight: 600;
    color: white;
    background-color: #0056b3;
    border: none;
    border-radius: 8px;
    text-decoration: none;
    text-align: left;
    transition: background-color 0.3s ease;
}
.button-simulateur:hover {
    background-color: #004494;
}
</style>
<div style="text-align: center;">
    <a href="?page=ANALYSE_CHAMPIONNAT" class="button-simulateur">Accéder au simulateur</a>
</div>
""", unsafe_allow_html=True)


# --- Lien vers la documentation ou aide
st.markdown("### Aide et Documentation")
st.markdown("Pour en savoir plus, consultez notre [guide d'utilisation](#) ou contactez-nous à [support@datafoot.fr](mailto:support@datafoot.fr).")
