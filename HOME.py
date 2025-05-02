import streamlit as st
from datetime import date

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import importlib
import simulateur_core
importlib.reload(simulateur_core)

# --- Configuration de la page principale ---
st.set_page_config(page_title="Datafoot.ai", page_icon="🏆", layout="wide")

# --- SIDEBAR ---
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

    # --- Bloc Connexion utilisateur existant ---
    st.subheader("📚 Déjà inscrit ?")

    user_name = st.text_input("Nom de l'utilisateur")
    user_email = st.text_input("Email")

    if st.button("Se connecter", key="btn_connexion_sidebar"):
        if user_name and user_email:
            st.session_state.user_name = user_name
            st.session_state.user_email = user_email
            st.session_state["user"] = user_email
            st.session_state.page = "home"
            st.success(f"Bienvenue {user_name} !")
        else:
            st.warning("Veuillez entrer votre nom et votre email.")

    # --- Bloc Inscription ---
    st.markdown("---")
    st.subheader("🆕 Créer un compte gratuit")

    with st.form("form_inscription"):
        prenom = st.text_input("Prénom")
        nom = st.text_input("Nom")
        email_inscription = st.text_input("Email")
        club = st.text_input("Club ou Société")

        st.markdown("📬 **Newsletter gratuite :** chaque semaine, recevez nos analyses sur les règles spéciales et égalités.")
        newsletter = st.checkbox("Je souhaite recevoir la newsletter")

        submitted = st.form_submit_button("Créer mon compte")

        if submitted:
            if prenom and nom and email_inscription and simulateur_core.verifier_email(email_inscription):
                st.session_state["user"] = email_inscription
                st.session_state["user_name"] = f"{prenom} {nom}"
                st.session_state["user_email"] = email_inscription
                st.session_state["club"] = club
                st.session_state["newsletter"] = "oui" if newsletter else "non"

                simulateur_core.enregistrer_inscription(
                    email=email_inscription,
                    prenom=prenom,
                    nom=nom,
                    societe_club=club,
                    newsletter="oui" if newsletter else "non",
                    source="simulateur"
                )

                st.success(f"Bienvenue {prenom} ! Ton compte est activé.")
            elif not simulateur_core.verifier_email(email_inscription):
                st.warning("L'adresse email saisie n'est pas valide.")
            else:
                st.warning("Merci de remplir tous les champs obligatoires.")

# --- Bloc Inscription Newsletter Seule ---
st.markdown("---")
st.subheader("📝 Inscription à la Newsletter")

with st.form("form_newsletter"):
    email_newsletter = st.text_input("Email pour la newsletter")
    submitted_newsletter = st.form_submit_button("S'inscrire à la newsletter")

    if submitted_newsletter:
        st.write(f"🧪 Debug email_newsletter = '{email_newsletter}'")
        st.write(f"📏 Longueur = {len(str(email_newsletter))}")
        st.write(f"📦 Type = {type(email_newsletter)}")
        st.write("📣 Appel réel à :", simulateur_core.verifier_email)

        test = simulateur_core.verifier_email(email_newsletter)
        st.write("🧪 Résultat brut validation email :", test)

        if email_newsletter and test:
            simulateur_core.enregistrer_inscription(
                email=email_newsletter,
                prenom="Non renseigné",
                nom="Non renseigné",
                societe_club="Non renseigné",
                newsletter="oui",
                source="newsletter seule"
            )
            st.success(f"✅ Vous êtes inscrit à la newsletter avec l'email {email_newsletter}.")
        elif not test:
            st.warning("L'adresse email saisie n'est pas valide.")
        else:
            st.warning("Merci de renseigner un email valide.")



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

with st.expander("🔧 Debug (session_state)"):
    st.write("Contenu de st.session_state :")
    st.json(st.session_state)

# --- Désactivation de la barre de navigation globale Streamlit ---
st.markdown(
    """
    <style>
    .css-1l02zws {
        display: none;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Initialiser la page courante ---
if "page" not in st.session_state:
    st.session_state.page = "home"

# --- PAGE D'ACCUEIL ---
st.title("Bienvenue sur Datafoot 👋")
st.subheader("Présentation du projet Datafoot ⚽")

# --- Message de connexion ---
if "user" in st.session_state:
    st.success(f"🔓 Connecté en tant que : {st.session_state['user_name']} ({st.session_state['user']})")
else:
    st.info("🔒 Connecte-toi ou crée un compte pour accéder à la simulation.")

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

# Bouton sobre aligné à gauche
st.markdown("""
<style>
.button-simulateur {
    display: inline-block;
    padding: 0.6rem 1.2rem;
    font-size: 1rem;
    font-weight: normal;
    color: #333333;
    background-color: #f0f0f0;
    border: 1px solid #cccccc;
    border-radius: 6px;
    text-decoration: none;
    text-align: left;
    transition: background-color 0.3s ease;
}
.button-simulateur:hover {
    background-color: #e6e6e6;
}
</style>
<a href="?page=ANALYSE_CHAMPIONNAT" class="button-simulateur">Accéder au simulateur</a>
""", unsafe_allow_html=True)


# --- Lien vers la documentation ou aide
st.markdown("### Aide et Documentation")
st.markdown("Pour en savoir plus, consultez notre [guide d'utilisation](#) ou contactez-nous à [support@datafoot.fr](mailto:support@datafoot.fr).")
