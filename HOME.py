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

    if st.button("Submit"):
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

        submitted = st.form_submit_button("Submit", type="primary")

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

# --- Bloc Intro ---
st.subheader("DATAFOOT.AI : Simulation & Analyses")
st.markdown("""
Datafoot.ai est un service dédié à l’analyse des matchs de football selon toutes ses composantes (club, équipe, joueur, arbitre, etc).  
Ce service s’appuie sur une plateforme de simulation et une newsletter qui décode et analyse l’ensemble des données.

<span style='color:gray; font-style:italic'>
Datafoot.ai is a service dedicated to football match analysis across all dimensions (club, team, player, referee, etc).  
It relies on a simulation platform and a newsletter that decodes and analyzes all the data.
</span>
""", unsafe_allow_html=True)

# --- Bloc Simulation ---
st.subheader("Plateforme de simulation")
st.markdown("""
- Compare les classements réels et simulés  
- Intègre les égalités particulières (confrontations directes) et les pénalités  
- Applique les règles spécifiques propres à chaque championnat (ex : moins bon 11e, top 2, etc.)  
- Évalue la difficulté du calendrier à venir (DIF_CAL)  

<span style='color:gray; font-style:italic'>
- Compare real and simulated standings  
- Includes special tie-breakers (head-to-head) and penalties  
- Applies competition-specific rules (e.g. worst 11th, best 2nd, etc.)  
- Evaluates upcoming schedule difficulty (DIF_CAL)
</span>
""", unsafe_allow_html=True)

# --- Bloc Newsletter / Insights ---
st.subheader("Newsletter dédiée aux analyses : exemples")
st.markdown("""
<div style='background-color:#f9f9f9; padding: 1rem; border-left: 4px solid #2E3C51; margin-top: 1rem;'>
<ol>
<li><b>Ligue 1</b><br>Qui possède le meilleur calendrier ?<br>
<i style='color:gray;'>Who has the easiest remaining schedule?</i></li>

<li><b>National 3</b><br>Qui seront les meilleurs 11e ?<br>
<i style='color:gray;'>Who will be the best-ranked 11th-placed teams?</i></li>

<li><b>Horaires</b><br>L'heure des matchs a-t-elle un impact sur les % de victoire à domicile ?<br>
<i style='color:gray;'>Does match time influence home win rates?</i></li>
</ol>
</div>

<br>
👉 Pour recevoir ce type d’analyse :  
<a href="https://datafootai.substack.com" target="_blank"><b>Inscrivez-vous à la newsletter</b></a><br>
<i style='color:gray;'>Subscribe to the newsletter.</i>
""", unsafe_allow_html=True)

# --- Bloc Data (en bas de page) ---
st.subheader("Données clés")
st.markdown("""
- **15 176 matchs** : répartis dans 56 championnats et 107 poules  
- **7 catégories** : U14 à SENIOR  
- **2 000+ équipes** couvertes, du national au régional  
- **Zooms renforcés** : U16 et U18 / Île-de-France et Hauts-de-France
""")

# --- Bouton vers le simulateur ---
st.markdown("""
<a href="/ANALYSE_CHAMPIONNAT" class="button-simulateur"> Simulation </a>
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

