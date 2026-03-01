def buscar_stats(player, p_id):
    print(f"🔎 Processando {player}")

    # 1️⃣ Buscar lista de partidas
    res_player = fazer_requisicao(f"{BASE_URL}/players/{p_id}")
    if not res_player or res_player.status_code != 200:
        return None

    matches = res_player.json()["data"]["relationships"]["matches"]["data"]

    total_kills = 0
    total_wins = 0
    total_assists = 0
    total_headshots = 0
    total_revives = 0
    total_damage = 0
    max_kill_dist = 0
    partidas_validas = 0

    for match in matches:

        match_id = match["id"]

        res_match = fazer_requisicao(f"{BASE_URL}/matches/{match_id}")
        if not res_match or res_match.status_code != 200:
            continue

        data = res_match.json()
        attributes = data["data"]["attributes"]

        # 2️⃣ Ignorar Casual
        if attributes.get("matchType") == "casual":
            continue

        # 3️⃣ Ignorar se não for squad
        if attributes.get("gameMode") != "squad":
            continue

        # 4️⃣ Verificar se é da temporada atual
        if attributes.get("seasonId") != current_season_id:
            continue

        # 5️⃣ Encontrar stats do player dentro da partida
        for included in data["included"]:
            if included["type"] == "participant":
                stats = included["attributes"]["stats"]
                if stats["playerId"] == p_id:

                    partidas_validas += 1
                    total_kills += stats.get("kills", 0)
                    total_assists += stats.get("assists", 0)
                    total_headshots += stats.get("headshotKills", 0)
                    total_revives += stats.get("revives", 0)
                    total_damage += stats.get("damageDealt", 0)

                    if stats.get("winPlace", 100) == 1:
                        total_wins += 1

                    longest = stats.get("longestKill", 0)
                    if longest > max_kill_dist:
                        max_kill_dist = longest

    if partidas_validas == 0:
        return None

    kr = round(total_kills / partidas_validas, 2)
    dano_medio = int(total_damage / partidas_validas)

    print(f"✅ {player} | {partidas_validas} partidas válidas")

    return (
        player,
        partidas_validas,
        kr,
        total_wins,
        total_kills,
        dano_medio,
        total_assists,
        total_headshots,
        total_revives,
        max_kill_dist,
        datetime.utcnow()
    )
