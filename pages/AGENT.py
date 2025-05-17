# --- pages/AGENT.py ---
import streamlit as st
import openai
import os
import sys
import json
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
openai.api_key = st.secrets["OPENAI_API_KEY"]

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

    # --- EXÉCUTION SI TOOL CALL ---
    if output.tool_calls:
        tool_call = output.tool_calls[0]
        tool_name = tool_call.function.name
        args = json.loads(tool_call.function.arguments)

        if tool_name == "get_classement_dynamique":
            try:
                df = get_classement_dynamique(
                    champ_id=args["champ_id"],
                    date=args["date"],
                    poule=args["poule"],
                    statut=args["statut"]
                )
                st.chat_message("assistant").dataframe(df, use_container_width=True)
            except Exception as e:
                st.chat_message("assistant").error(f"Erreur lors de l'exécution : {e}")
    else:
        st.chat_message("assistant").write(output.content or "[Réponse générée par l'agent]")
