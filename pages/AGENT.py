# --- pages/AGENT.py ---
import streamlit as st
import openai
import os
import sys
import json
import pandas as pd
from datetime import date
from simulateur_core import get_classement_dynamique, appliquer_penalites, trier_et_numeroter
from agents_core import get_id_championnat

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
openai.api_key = os.getenv("OPENAI_API_KEY")

# --- CHAT INPUT ---
if prompt := st.chat_input("Pose ta question sur les classements…"):
    st.chat_message("user").write(prompt)

    # --- SYSTEM PROMPT ---
    system_prompt = (
        "Tu es un agent Datafoot spécialisé dans l'analyse des classements. "
        "Tu disposes de fonctions Python pour récupérer et trier les classements. "
        "Si l'utilisateur mentionne un nom de championnat (ex: 'U19', 'N3'), utilise immédiatement la fonction get_id_championnat pour obtenir l'identifiant correspondant. "
        "Ne demande pas confirmation si le nom semble explicite. "
        "Utilise ensuite cet ID dans les fonctions de classement. "
        "Réponds toujours en t'appuyant sur les outils disponibles."
    )

    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_classement_dynamique",
                "description": "Retourne le classement dynamique d’un championnat donné à une date précise.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ID_CHAMPIONNAT": {"type": "integer"},
                        "date": {"type": "string", "format": "date"},
                        "poule": {"type": "string"},
                        "statut": {"type": "string"}
                    },
                    "required": ["ID_CHAMPIONNAT", "date", "poule", "statut"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "appliquer_penalites",
                "description": "Applique les pénalités à un classement donné selon la date et le championnat.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "classement": {"type": "string", "description": "Classement au format JSON"},
                        "ID_CHAMPIONNAT": {"type": "integer"},
                        "date": {"type": "string", "format": "date"}
                    },
                    "required": ["classement", "ID_CHAMPIONNAT", "date"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "trier_et_numeroter",
                "description": "Trie et numérote le classement final selon les règles de classement Datafoot.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "classement": {"type": "string", "description": "Classement au format JSON"}
                    },
                    "required": ["classement"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_id_championnat",
                "description": "Retourne l'identifiant du championnat à partir de son nom.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "nom": {"type": "string"}
                    },
                    "required": ["nom"]
                }
            }
        }
    ]

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]

    loop_counter = 0
    while loop_counter < 5:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )

        output = response.choices[0].message
        messages.append(output)

        if output.tool_calls:
            for tool_call in output.tool_calls:
                tool_name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)

                try:
                    if tool_name == "get_classement_dynamique":
                        df = get_classement_dynamique(
                            ID_CHAMPIONNAT=args["ID_CHAMPIONNAT"],
                            date=args["date"],
                            poule=args["poule"],
                            statut=args["statut"]
                        )
                        result = df.to_json(orient="records")

                    elif tool_name == "appliquer_penalites":
                        df = pd.read_json(args["classement"])
                        df = appliquer_penalites(df, ID_CHAMPIONNAT=args["ID_CHAMPIONNAT"], date=args["date"])
                        result = df.to_json(orient="records")

                    elif tool_name == "trier_et_numeroter":
                        df = pd.read_json(args["classement"])
                        df = trier_et_numeroter(df)
                        result = df.to_json(orient="records")

                    elif tool_name == "get_id_championnat":
                        nom = args["nom"]
                        result = get_id_championnat(nom)

                    else:
                        result = f"Fonction {tool_name} non reconnue."

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": str(result)
                    })

                except Exception as e:
                    st.chat_message("assistant").error(f"Erreur dans {tool_name} : {e}")
                    break

        else:
            st.chat_message("assistant").write(output.content or "[Réponse générée par l'agent]")
            break

        loop_counter += 1
