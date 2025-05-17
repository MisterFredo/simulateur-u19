# --- pages/AGENT.py ---
import streamlit as st
import openai
import os
import sys
from datetime import date
from simulateur_core import get_classement_dynamique, appliquer_penalites, trier_et_numeroter

# --- CONFIG STREAMLIT ---
st.set_page_config(page_title="Agent Datafoot", page_icon="🤖", layout="wide")
st.title("🧠 Agent Datafoot – Analyste Classement")

# --- CHOIX DU RÔLE ---
role = st.selectbox("Choisis ton agent", ["Analyste Classement"], index=0)

if role == "Analyste Classement":
    st.markdown(
        "> Cet agent analyse les classements par championnat, poule, date et statut. Il peut inclure les pénalités."
    )

# --- CLÉ OPENAI ---
openai.api_key = os.getenv("OPENAI_API_KEY")  # ⚠️ Stockée dans secrets ou env vars

# --- CHAT INPUT ---
if prompt := st.chat_input("Pose ta question sur les classements…"):
    st.chat_message("user").write(prompt)

    # --- SYSTEM PROMPT ---
    system_prompt = (
        "Tu es un agent Datafoot spécialisé dans l'analyse des classements. "
        "Tu disposes de fonctions Python pour récupérer et trier les classements. "
        "Pose des questions si nécessaire et réponds de manière claire."
    )

    # --- TOOLS (fonctions exposées) ---
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_classement_dynamique",
                "description": "Retourne le classement dynamique d’un championnat donné à une date précise.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "champ_id": {"type": "integer"},
                        "date": {"type": "string", "format": "date"},
                        "poule": {"type": "string"},
                        "statut": {"type": "string"}
                    },
                    "required": ["champ_id", "date", "poule", "statut"]
                }
            }
        }
    ]

    # --- MESSAGES ---
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]

    # --- APPEL OPENAI ---
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        tools=tools,
        tool_choice="auto"
    )

    output = response.choices[0].message
    st.chat_message("assistant").write(output.content or "[Réponse générée par l'agent]")
