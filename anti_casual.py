import requests
import time
import os
import psycopg2

API_KEY = os.getenv("PUBG_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
SHARD = "steam"

PLAYERS = {
    "Mamutag_Komander": "account.64c62d76cce74d0b99857a27975e350e",
    "Adrian-Wan":"account.58beb24ada7346408942d42dc64c7901",
    "MironoteuCool":"account.24b0600cbba342eab1546ae2881f50fa",
    "FabioEspeto":"account.d8ccad228a4a417dad9921616d6c6bcd",
    "Robson_Foz":"account.8142e6d837254ee1bca954b719692f38",
    "MEIRAA":"account.c3f37890e7534978abadaf4bae051390",
    "EL-LOCORJ":"account.94ab932726fc4c64a03eb9797429baa3",
    "SalaminhoKBD":"account.de093e200d3441a9b781a9717a017dd3",
    "nelio_ponto_dev":"account.ad39c88ddf754d33a3dfeadc117c47df",
    "CARNEIROOO":"account.8c0313f2148d47b7bffcde634f094445",
    "Kowalski_PR":"account.b25200afe120424a839eb56dd2bc49cb",
    "Zacouteguy":"account.a742bf1d5725467c91140cd0ed83c265",
    "Sidors":"account.60ab21fad4094824a32dc404420b914d",
    "Takato_Matsuki":"account.10d2403139bd4066a95dda1a3eefe1e8",
    "cmm01":"account.80cedebb935242469fdd177454a52e0e",
    "Petrala":"account.aadd1c378ff841219d853b4ad2646286",
    "Fumiga_BR":"account.1fa2a7c08c3e4d4786587b4575a071cb",
    "O-CARRASCO":"account.78c6f7bd39da4274b5a3196ac624e92e",
}

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Accept": "application/vnd.api+json"
}


def get(url):
    r = requests.get(url, headers=HEADERS)
    if r.status_code == 200:
        return r.json()
    return None


def match_ja_processada(conn, match_id):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM matches_processadas WHERE match_id = %s",
            (match_id,)
        )
        return cur.fetchone() is not None


def salvar_match_processada(conn, dados):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO matches_processadas
            (match_id, season_id, game_mode, map_name, match_type, humanos, bots)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (match_id) DO NOTHING
        """, dados)
    conn.commit()


def detectar_casual(attr, humanos):
    if attr.get("matchType") == "casual":
        return True
    if humanos <= 12:
        return True
    return False


def processar_player(conn, player_name, player_id):
    print(f"\n🔎 Player: {player_name}")

    player_data = get(f"https://api.pubg.com/shards/{SHARD}/players/{player_id}")
    if not player_data:
        return

    matches = player_data["data"]["relationships"]["matches"]["data"]

    for m in matches:
        match_id = m["id"]

        if match_ja_processada(conn, match_id):
            continue

        match_data = get(f"https://api.pubg.com/shards/{SHARD}/matches/{match_id}")
        if not match_data:
            continue

        attr = match_data["data"]["attributes"]

        if attr.get("gameMode") != "squad":
            continue

        participants = [
            x for x in match_data["included"]
            if x["type"] == "participant"
        ]

        humanos = sum(
            1 for p in participants
            if p["attributes"]["stats"].get("playerId", "").startswith("account.")
        )

        bots = len(participants) - humanos

        casual = detectar_casual(attr, humanos)

        print(f"Match: {match_id}")
        print("Casual:", casual)

        # 🔥 Se NÃO for casual → aqui você soma no ranking
        if not casual:
            print(">>> SOMAR STATS AO RANKING <<<")
            # aqui você integra com sua lógica atual

        salvar_match_processada(conn, (
            match_id,
            attr.get("seasonId"),
            attr.get("gameMode"),
            attr.get("mapName"),
            attr.get("matchType"),
            humanos,
            bots
        ))

        time.sleep(0.7)


def main():
    conn = psycopg2.connect(DATABASE_URL)

    for name, pid in PLAYERS.items():
        processar_player(conn, name, pid)

    conn.close()


if __name__ == "__main__":
    main()
