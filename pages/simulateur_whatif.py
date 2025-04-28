# --- 3. MATCHS À SIMULER
filtrer_non_joues = st.checkbox("Afficher uniquement les matchs non joués", value=True)

matchs_simulables = get_matchs_modifiables(champ_id, date_limite, filtrer_non_joues)

if selected_poule != "Toutes les poules":
    matchs_simulables = matchs_simulables[matchs_simulables["POULE"] == selected_poule]

st.markdown("### 🎯 Matchs à simuler")
if matchs_simulables.empty:
    st.info("Aucun match disponible pour cette configuration.")
    st.stop()

# --- Data editor simplifié (pas d'ID affichés)
edited_df = st.data_editor(
    matchs_simulables[[
        "JOURNEE", "POULE", "DATE",
        "EQUIPE_DOM", "NB_BUT_DOM",
        "EQUIPE_EXT", "NB_BUT_EXT"
    ]],
    num_rows="dynamic",
    use_container_width=True,
    key="simulation_scores"
)

# --- 4. VALIDATION SIMULATION
valider = st.button("🔁 Recalculer le classement avec ces scores simulés")

# --- 5. SIMULATION SEULEMENT SI VALIDATION
if valider:

    df_valid = edited_df.dropna(subset=["NB_BUT_DOM", "NB_BUT_EXT"])

    if df_valid.empty:
        st.warning("🚫 Aucun score simulé valide.")
    else:
        # --- Affichage des matchs simulés pour rappel
        st.markdown("### 📝 Matchs simulés")
        def color_victory(val_dom, val_ext):
            if val_dom > val_ext:
                return ["background-color: lightgreen", "background-color: lightcoral"]
            elif val_dom < val_ext:
                return ["background-color: lightcoral", "background-color: lightgreen"]
            else:
                return ["background-color: lightyellow", "background-color: lightyellow"]

        matchs_affichage = df_valid[[
            "JOURNEE", "POULE", "DATE", "EQUIPE_DOM", "NB_BUT_DOM", "EQUIPE_EXT", "NB_BUT_EXT"
        ]].copy()

        if not matchs_affichage.empty:
            styled_matchs = matchs_affichage.style.apply(
                lambda row: color_victory(row["NB_BUT_DOM"], row["NB_BUT_EXT"]),
                subset=["NB_BUT_DOM", "NB_BUT_EXT"],
                axis=1
            )
            st.dataframe(styled_matchs, use_container_width=True)

        # --- Fusion des matchs terminés + matchs simulables
        matchs_tous = pd.concat([matchs_termine, matchs_simulables], ignore_index=True)

        # --- Remplacer uniquement les scores réellement simulés
        for idx, row in df_valid.iterrows():
            id_match = matchs_simulables.iloc[idx]["ID_MATCH"]  # récupérer l'ID_MATCH original
            if not pd.isna(row["NB_BUT_DOM"]) and not pd.isna(row["NB_BUT_EXT"]):
                matchs_tous.loc[matchs_tous["ID_MATCH"] == id_match, "NB_BUT_DOM"] = int(row["NB_BUT_DOM"])
                matchs_tous.loc[matchs_tous["ID_MATCH"] == id_match, "NB_BUT_EXT"] = int(row["NB_BUT_EXT"])

        # --- Sécurisation : ne garder que les matchs avec scores complets
        matchs_tous = matchs_tous.dropna(subset=["NB_BUT_DOM", "NB_BUT_EXT"])

        # --- Recalcul du classement
        classement_simule = get_classement_dynamique(champ_id, date_limite, matchs_override=matchs_tous)
        classement_simule = appliquer_penalites(classement_simule, date_limite)
        classement_simule, mini_classements_simule = appliquer_diff_particuliere(classement_simule, matchs_tous)
        classement_simule = trier_et_numeroter(classement_simule, type_classement)

        # --- Confirmation utilisateur
        st.success("✅ Simulation recalculée avec succès !")

        # --- Affichage du nouveau classement simulé
        st.markdown("### 🧪 Nouveau Classement simulé")
        for poule in sorted(classement_simule["POULE"].unique()):
            st.subheader(f"Poule {poule}")
            classement_poule = classement_simule[classement_simule["POULE"] == poule]
            colonnes_finales = [col for col in colonnes if col in classement_poule.columns]
            st.dataframe(classement_poule[colonnes_finales], use_container_width=True)

        # --- Mini-classements des égalités
        if mini_classements_simule:
            st.markdown("### Mini-classements des égalités particulières 🥇 (Simulation)")
            for (poule, pts), mini in mini_classements_simule.items():
                with st.expander(f"Poule {poule} – Égalité à {pts} points", expanded=True):
                    st.markdown("**Mini-classement :**")
                    st.dataframe(mini["classement"], use_container_width=True)
                    st.markdown("**Matchs concernés :**")
                    st.dataframe(mini["matchs"], use_container_width=True)

        # --- Affichage comparatifs spéciaux
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
