import streamlit as st

# ✅ Doit absolument être la première commande
st.set_page_config(page_title="Datafoot.ai", page_icon="🏆", layout="wide")

# --- Imports utiles ---
import pandas as pd
from datetime import date, datetime

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import importlib
import simulateur_core
importlib.reload(simulateur_core)

from simulateur_core import (
    enregistrer_inscription,
)

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

    # --- Connexion utilisateur ---
    st.subheader("Connexion / Login")

    user_name = st.text_input("Nom / Name")
    user_email = st.text_input("Email")

    if st.button("Submit", key="btn_connexion_sidebar"):
        if user_name and user_email:
            st.session_state.user_name = user_name
            st.session_state.user_email = user_email
            st.session_state["user"] = user_email
            st.session_state.page = "home"
            st.success("Connexion réussie. / Login successful.")
        else:
            st.warning("Merci de renseigner nom et email. / Please fill in name and email.")

    # --- Inscription ---
    st.markdown("---")
    st.subheader("Créer un compte / Create an Account")

    with st.form("form_inscription"):
        prenom = st.text_input("Prénom / First Name")
        nom = st.text_input("Nom / Last Name")
        email_inscription = st.text_input("Email")
        club = st.text_input("Club / Company")

        st.markdown("Newsletter DATAFOOT.AI : analyses & insights")
        newsletter = st.checkbox("S'abonner / Subscribe")

        submitted = st.form_submit_button("Créer / Create")

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

                st.success("Compte activé. / Account activated.")
            else:
                st.warning("Tous les champs sont requis. / All fields are required.")


# --- Style moderne du contenu principal ---
st.markdown(
    """
    <style>
    [data-testid="stAppViewContainer"] {
        background-color: #ffffff;
        padding: 2rem;
    }
    h1, h2, h3 {
        color: #2E3C51;
        font-family: 'Poppins', 'Segoe UI', sans-serif;
    }
    img {
        height: auto !important;
        max-width: 100%;
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
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Message de connexion (neutre) ---
if "user" in st.session_state:
    st.success(f"Connecté : {st.session_state['user_name']} ({st.session_state['user']})")
else:
    st.info("Simuler ? Connexion requise / Want to simulate? Login required")

# --- Bloc concept ---
st.subheader("Concept")
st.markdown("""
Datafoot.ai est une plateforme dédiée à l’analyse et à la simulation des championnats de football amateur.  
Elle permet de consulter les classements en temps réel, tester différents scénarios, et appliquer des règles spéciales (U19, N3, etc.) selon les règlements fédéraux.
""")

# --- Bloc fonctionnalités ---
st.subheader("Fonctionnalités principales")
st.markdown("""
- **Classements dynamiques** : Calculés à partir des résultats à une date donnée  
- **Simulation de matchs** : Modifier les scores pour tester des scénarios  
- **Règles spéciales** : Classements personnalisés pour U19, U17, N2, N3  
- **Égalités** : Départager les équipes par différence particulière
""")

# --- Bloc analyses (encadré visuel) ---
st.markdown("""
<div style='background-color:#f9f9f9; padding: 1rem; border-left: 4px solid #2E3C51; margin-top: 2rem;'>
<h4 style='margin-top:0;'>Exemples d’analyses</h4>
<ol>
<li><b>U19 : un 11e devant un 10e</b><br>Grâce aux confrontations directes contre les équipes classées 6 à 10.</li>
<li><b>National 3 : un 10e sauvé</b><br>Grâce aux résultats contre les 5e à 9e.</li>
<li><b>Égalité parfaite</b><br>Départagée par la règle de différence particulière.</li>
</ol>
</div>
""", unsafe_allow_html=True)

# --- Bouton unique vers la simulation ---
st.markdown("""
<a href="/ANALYSE_CHAMPIONNAT" class="button-simulateur"> Simulation (FR/EN)</a>
""", unsafe_allow_html=True)

st.markdown("""
<style>
.button-simulateur {
    display: inline-block;
    padding: 0.6rem 1.2rem;
    font-size: 1rem;
    font-weight: normal;
    color: #2E3C51;
    background-color: #f0f0f0;
    border: 1px solid #cccccc;
    border-radius: 6px;
    text-decoration: none;
    transition: background-color 0.3s ease;
}
.button-simulateur:hover {
    background-color: #e6e6e6;
}
</style>
""", unsafe_allow_html=True)

