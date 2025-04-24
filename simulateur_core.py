import pandas as pd

def get_type_classement(client, champ_id):
    query = f"""
        SELECT CLASSEMENT
        FROM `datafoot-448514.DATAFOOT.DATAFOOT_CHAMPIONNAT`
        WHERE ID_CHAMPIONNAT = {champ_id}
        LIMIT 1
    """
    result = client.query(query).to_dataframe()
    return result.iloc[0]["CLASSEMENT"] if not result.empty else "GENERALE"

def get_classement_dynamique(client, champ_id, date_limite):
    query = f"""
        WITH matchs_termine AS (
          SELECT *
          FROM `datafoot-448514.DATAFOOT.DATAFOOT_MATCH_2025`
          WHERE STATUT = 'TERMINE'
            AND ID_CHAMPIONNAT = {champ_id}
            AND DATE <= DATE('{date_limite}')
        ),
        match_equipes AS (
          SELECT ID_CHAMPIONNAT, POULE, ID_EQUIPE_DOM AS ID_EQUIPE, EQUIPE_DOM AS NOM_EQUIPE,
                 NB_BUT_DOM AS BUTS_POUR, NB_BUT_EXT AS BUTS_CONTRE,
                 CASE WHEN NB_BUT_DOM > NB_BUT_EXT THEN 3 WHEN NB_BUT_DOM = NB_BUT_EXT THEN 1 ELSE 0 END AS POINTS
          FROM matchs_termine
          UNION ALL
          SELECT ID_CHAMPIONNAT, POULE, ID_EQUIPE_EXT, EQUIPE_EXT, NB_BUT_EXT, NB_BUT_DOM,
                 CASE WHEN NB_BUT_EXT > NB_BUT_DOM THEN 3 WHEN NB_BUT_EXT = NB_BUT_DOM THEN 1 ELSE 0 END
          FROM matchs_termine
        ),
        classement AS (
          SELECT ID_CHAMPIONNAT, POULE, ID_EQUIPE, NOM_EQUIPE,
                 COUNT(*) AS MJ,
                 SUM(CASE WHEN POINTS = 3 THEN 1 ELSE 0 END) AS G,
                 SUM(CASE WHEN POINTS = 1 THEN 1 ELSE 0 END) AS N,
                 SUM(CASE WHEN POINTS = 0 THEN 1 ELSE 0 END) AS P,
                 SUM(BUTS_POUR) AS BP,
                 SUM(BUTS_CONTRE) AS BC,
                 SUM(BUTS_POUR - BUTS_CONTRE) AS DIFF,
                 SUM(POINTS) AS PTS
          FROM match_equipes
          GROUP BY ID_CHAMPIONNAT, POULE, ID_EQUIPE, NOM_EQUIPE
        )
        SELECT *, RANK() OVER (PARTITION BY ID_CHAMPIONNAT, POULE ORDER BY PTS DESC, DIFF DESC, BP DESC) AS CLASSEMENT
        FROM classement
        ORDER BY POULE, CLASSEMENT
    """
    df = client.query(query).to_dataframe()
    return df.rename(columns={"PTS": "POINTS"})

def get_matchs_termine(client, champ_id, date_limite):
    query = f"""
        SELECT *
        FROM `datafoot-448514.DATAFOOT.DATAFOOT_MATCH_2025`
        WHERE STATUT = 'TERMINE'
          AND ID_CHAMPIONNAT = {champ_id}
          AND DATE <= DATE('{date_limite}')
    """
    return client.query(query).to_dataframe()

def appliquer_diff_particuliere(classement_df, matchs_df, selected_poule="Toutes les poules"):
    classement_df["RANG_CONFRONT"] = 999
    mini_classements = {}

    groupes = classement_df.copy()
    groupes = groupes[groupes.duplicated(subset=["POULE", "POINTS"], keep=False)]
    groupes = groupes.groupby(["POULE", "POINTS"])

    for (poule, pts), groupe in groupes:
        if selected_poule != "Toutes les poules" and poule != selected_poule:
            continue

        equipes_concernees = groupe["ID_EQUIPE"].tolist()

        matchs_confrontations = matchs_df[
            (matchs_df["ID_EQUIPE_DOM"].isin(equipes_concernees)) &
            (matchs_df["ID_EQUIPE_EXT"].isin(equipes_concernees))
        ]

        mini_classement = []
        for equipe_id in equipes_concernees:
            matchs_eq = matchs_confrontations[
                (matchs_confrontations["ID_EQUIPE_DOM"] == equipe_id) |
                (matchs_confrontations["ID_EQUIPE_EXT"] == equipe_id)
            ]

            points = 0
            diff_buts = 0
            for _, row in matchs_eq.iterrows():
                if row["ID_EQUIPE_DOM"] == equipe_id:
                    bp, bc = row["NB_BUT_DOM"], row["NB_BUT_EXT"]
                else:
                    bp, bc = row["NB_BUT_EXT"], row["NB_BUT_DOM"]

                if bp > bc:
                    points += 3
                elif bp == bc:
                    points += 1
                diff_buts += bp - bc

            nom_equipe = groupe[groupe["ID_EQUIPE"] == equipe_id]["NOM_EQUIPE"].values[0]
            mini_classement.append({
                "ID_EQUIPE": equipe_id,
                "NOM_EQUIPE": nom_equipe,
                "PTS_CONFRONT": points,
                "DIFF_CONFRONT": diff_buts
            })

        mini_df = pd.DataFrame(mini_classement)
        mini_df = mini_df.sort_values(by=["PTS_CONFRONT", "DIFF_CONFRONT"], ascending=[False, False])
        mini_df["RANG_CONFRONT"] = range(1, len(mini_df) + 1)

        for _, row in mini_df.iterrows():
            classement_df.loc[classement_df["ID_EQUIPE"] == row["ID_EQUIPE"], "RANG_CONFRONT"] = row["RANG_CONFRONT"]

        mini_classements[(poule, pts)] = {
            "classement": mini_df.drop(columns=["ID_EQUIPE"]),
            "matchs": matchs_confrontations[["DATE", "EQUIPE_DOM", "EQUIPE_EXT", "NB_BUT_DOM", "NB_BUT_EXT"]].sort_values("DATE")
        }

    return classement_df, mini_classements

@st.cache_data(show_spinner=False)
def get_poules_temp(client, champ_id):
    query = f"""
        SELECT DISTINCT POULE
        FROM `datafoot-448514.DATAFOOT.DATAFOOT_MATCH_2025`
        WHERE ID_CHAMPIONNAT = {champ_id}
          AND POULE IS NOT NULL
        ORDER BY POULE
    """
    return client.query(query).to_dataframe()
