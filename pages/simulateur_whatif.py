# --- Titre
st.title(f"🧪 Simulateur – {selected_nom}")

# --- Chargement classement actuel
matchs_termine = get_matchs_termine(champ_id, date_limite)
classement_initial = get_classement_dynamique(champ_id, date_limite, matchs_override=matchs_termine)
classement_initial = appliquer_penalites(classement_initial, date_limite)
classement_initial = trier_et_numeroter(classement_initial, type_classement)

# --- Affichage classement actuel
st.markdown("### 🏆 Classement actuel")
for poule in sorted(classement_initial["POULE"].unique()):
    st.subheader(f"Poule {poule}")
    classement_poule = classement_initial[classement_initial["POULE"] == poule]
    colonnes = ["CLASSEMENT", "NOM_EQUIPE", "POINTS", "PENALITES", "MJ", "G", "N", "P", "BP", "BC", "DIFF"]
    colonnes_finales = [col for col in colonnes if col in classement_poule.columns]
    st.dataframe(classement_poule[colonnes_finales], use_container_width=True)

# --- Affichage mini-classements du classement actuel
classement_initial, mini_classements_initial = appliquer_diff_particuliere(classement_initial, matchs_termine)

if mini_classements_initial:
    st.markdown("### Mini-classements des égalités particulières 🥇 (Classement actuel)")
    for (poule, pts), mini in mini_classements_initial.items():
        with st.expander(f"Poule {poule} – Égalité à {pts} points", expanded=True):
            st.markdown("**Mini-classement :**")
            st.dataframe(mini["classement"], use_container_width=True)
            st.markdown("**Matchs concernés :**")
            st.dataframe(mini["matchs"], use_container_width=True)

# --- Chargement matchs simulables
filtrer_non_joues = st.checkbox("Afficher uniquement les matchs non joués", value=True)

matchs_simulables = get_matchs_modifiables(champ_id, date_limite, filtrer_non_joues)

if selected_poule != "Toutes les poules":
    matchs_simulables = matchs_simulables[matchs_simulables["POULE"] == selected_poule]

# --- Affichage matchs simulables
st.markdown("### 🎯 Matchs à simuler")
if matchs_simulables.empty:
    st.info("Aucun match disponible pour cette configuration.")
    st.stop()

edited_df = st.data_editor(
    matchs_simulables[[
        "ID_MATCH", "JOURNEE", "POULE", "DATE",
        "ID_EQUIPE_DOM", "EQUIPE_DOM", "NB_BUT_DOM",
        "ID_EQUIPE_EXT", "EQUIPE_EXT", "NB_BUT_EXT"
    ]],
    num_rows="dynamic",
    use_container_width=True,
    key="simulation_scores"
)

# --- Simulation sur bouton
if st.button("🔁 Recalculer le classement avec ces scores simulés"):

    df_valid = edited_df.dropna(subset=["NB_BUT_DOM", "NB_BUT_EXT"])

    if df_valid.empty:
        st.warning("🚫 Aucun score simulé valide.")
    else:
        # Fusion matchs terminés + modifiables
        matchs_tous = pd.concat([matchs_termine, matchs_simulables], ignore_index=True)

        for idx, row in df_valid.iterrows():
            id_match = row["ID_MATCH"]
            matchs_tous.loc[matchs_tous["ID_MATCH"] == id_match, "NB_BUT_DOM"] = row["NB_BUT_DOM"]
            matchs_tous.loc[matchs_tous["ID_MATCH"] == id_match, "NB_BUT_EXT"] = row["NB_BUT_EXT"]

        # Recalcul du classement simulé
        classement_simule = get_classement_dynamique(champ_id, date_limite, matchs_override=matchs_tous)
        classement_simule = appliquer_penalites(classement_simule, date_limite)
        classement_simule, mini_classements_simule = appliquer_diff_particuliere(classement_simule, matchs_tous)
        classement_simule = trier_et_numeroter(classement_simule, type_classement)

        # Affichage du nouveau classement
        st.markdown("### 🧪 Nouveau Classement simulé")
        for poule in sorted(classement_simule["POULE"].unique()):
            st.subheader(f"Poule {poule}")
            classement_poule = classement_simule[classement_simule["POULE"] == poule]
            colonnes_finales = [col for col in colonnes if col in classement_poule.columns]
            st.dataframe(classement_poule[colonnes_finales], use_container_width=True)

        # Affichage mini-classements simulés
        if mini_classements_simule:
            st.markdown("### Mini-classements des égalités particulières 🥇 (Simulation)")
            for (poule, pts), mini in mini_classements_simule.items():
                with st.expander(f"Poule {poule} – Égalité à {pts} points", expanded=True):
                    st.markdown("**Mini-classement :**")
                    st.dataframe(mini["classement"], use_container_width=True)
                    st.markdown("**Matchs concernés :**")
                    st.dataframe(mini["matchs"], use_container_width=True)

        # Affichage comparatifs spéciaux
        if selected_poule == "Toutes les poules":
            if champ_id == 6:
                st.markdown("### 🚨 Comparatif spécial U19")
                df_11e = classement_special_u19(classement_simule, champ_id, date_limite)
                if df_11e is not None:
                    st.dataframe(df_11e, use_container_width=True)

            if champ_id == 7:
                st.markdown("### 🥈 Comparatif spécial U17")
                df_2e = classement_special_u17(classement_simule, champ_id, date_limite)
                if df_2e is not None:
                    st.dataframe(df_2e, use_container_width=True)

            if champ_id == 4:
                st.markdown("### 🚨 Comparatif spécial N2")
                df_13e = classement_special_n2(classement_simule, champ_id, date_limite)
                if df_13e is not None:
                    st.dataframe(df_13e, use_container_width=True)

            if champ_id == 5:
                st.markdown("### ⚠️ Comparatif spécial N3")
                df_10e = classement_special_n3(classement_simule, champ_id, date_limite)
                if df_10e is not None:
                    st.dataframe(df_10e, use_container_width=True)
