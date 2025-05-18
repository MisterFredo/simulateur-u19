# --- pages/AGENT.py ---
import streamlit as st
import openai
import os
import sys
import json
import pandas as pd
from datetime import date
from simulateur_core import get_classement_dynamique, appliquer_penalites, trier_et_numeroter, get_type_classement
from agents_core import get_id_championnat

# --- ACCÈS RÉSERVÉ À FREDERIC ---
if st.session_state.get("user_email") != "mister.fredo@gmail.com":
    st.warning("🚫 Accès réservé à l’administrateur.")
    st.stop()

st.set_page_config(page_title="Agent Datafoot", page_icon="🤖", layout="wide")
st.title("🧠 Agent Datafoot – Analyste Classement")

role = st.selectbox("Choisis ton agent", ["Analyste Classement"], index=0)

if role == "Analyste Classement":
    st.markdown(
        "> Cet agent analyse les classements par championnat, poule, date. Il peut inclure les pénalités."
    )

openai.api_key = os.getenv("OPENAI_API_KEY")

# Mémoire locale persistante sur la session
if "memory_context" not in st.session_state:
    st.session_state.memory_context = {}

if prompt := st.chat_input("Pose ta question sur les classements…"):
    st.chat_message("user").write(prompt)

    system_prompt = (
        "Tu es un agent Datafoot spécialisé dans l'analyse des classements. "
        "Tu disposes de fonctions Python pour récupérer et trier les classements. "
        "Si l'utilisateur mentionne un nom de championnat (ex: 'U19', 'N3'), utilise immédiatement la fonction get_id_championnat pour obtenir l'identifiant correspondant. "
        "Ne demande pas confirmation si le nom semble explicite. "
        "Utilise ensuite cet ID dans les fonctions de classement. "
        "Si l'utilisateur répond avec une précision (ex: 'U17 National'), complète le contexte précédent."
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
                        "id_championnat": {"type": "integer"},
                        "date_limite": {"type": "string", "format": "date"}
                    },
                    "required": ["id_championnat", "date_limite"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "appliquer_penalites",
                "description": "Applique les pénalités à un classement donné selon la date.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "classement": {"type": "string"},
                        "date_limite": {"type": "string", "format": "date"}
                    },
                    "required": ["classement", "date_limite"]
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
                        "classement": {"type": "string"},
                        "type_classement": {"type": "string"}
                    },
                    "required": ["classement", "type_classement"]
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

    memory = st.session_state.memory_context
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
                        memory.update({
                            "id_championnat": args["id_championnat"],
                            "date_limite": args["date_limite"]
                        })
                        df = get_classement_dynamique(
                            id_championnat=args["id_championnat"],
                            date_limite=args["date_limite"]
                        )
                        if df.empty:
                            raise ValueError("Aucun match trouvé pour les paramètres fournis.")
                        if memory.get("poule"):
                            df = df[df["POULE"] == memory["poule"]]
                        result = df.to_json(orient="records")

                    elif tool_name == "appliquer_penalites":
                        df = pd.read_json(args["classement"])
                        if df.empty or "ID_EQUIPE" not in df.columns:
                            raise ValueError("Classement vide ou mal structuré pour appliquer les pénalités.")
                        df = appliquer_penalites(df, date_limite=args["date_limite"])
                        result = df.to_json(orient="records")

                    elif tool_name == "trier_et_numeroter":
                        df = pd.read_json(args["classement"])
                        df = trier_et_numeroter(df, type_classement=args.get("type_classement", "GENERALE"))
                        result = df.to_json(orient="records")

                    elif tool_name == "get_id_championnat":
                        nom = args["nom"]
                        result_obj = get_id_championnat(nom)
                        try:
                            result_json = json.loads(result_obj)
                            memory.update(result_json)
                            result = str(result_json["id_championnat"])
                        except:
                            result = result_obj

                    else:
                        result = f"Fonction {tool_name} non reconnue."

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": str(result)
                    })

                except Exception as e:
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": f"Erreur dans {tool_name} : {str(e)}"
                    })
                    st.chat_message("assistant").error(f"Erreur dans {tool_name} : {e}")

        else:
            st.chat_message("assistant").write(output.content or "[Réponse générée par l'agent]")
            break

        loop_counter += 1
