import streamlit as st
import requests
import pandas as pd
from sqlalchemy import create_engine, text

# =============================
# CONFIGURAÇÃO DA PÁGINA
# =============================
st.set_page_config(
    page_title="Ranking Squad - Season Atual",
    layout="wide",
    page_icon="🎮"
)

st.title("🎮 Ranking Squad - Season Atual (Normal TPP)")

# =============================
# CONFIGURAÇÕES (SECRETS)
# =============================
API_KEY = st.secrets["PUBG_API_KEY"]
DATABASE_URL = st.secrets["DATABASE_URL"]

engine = create_engine(DATABASE_URL)

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Accept": "application/vnd.api+json"
}

# =============================
# FUNÇÃO PARA PEGAR SEASON ATUAL
# =============================
@st.cache_data(ttl=3600)
def get_current_season():
    url = "https://api.pubg.com/shards/steam/seasons"
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        st.error("Erro ao buscar season atual")
        return None

    seasons = response.json()["data"]

    current_season = next(
        s["id"] for s in seasons
        if s["attributes"]["isCurrentSeason"] is True
    )

    return current_season

# =============================
# FUNÇÃO PARA PEGAR PLAYER ID
# =============================
def get_player_id(nickname):
    url = f"https://api.pubg.com/shards/steam/players?filter[playerNames]={nickname}"
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        return None

    data = response.json()["data"]
    if not data:
        return None

    return data[0]["id"]

# =============================
# FUNÇÃO PARA PEGAR STATS (SQUAD NORMAL TPP)
# =============================
def get_squad_stats(player_id, season_id):
    url = f"https://api.pubg.com/shards/steam/players/{player_id}/seasons/{season_id}"
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        return None

    data = response.json()
    game_modes = data["data"]["attributes"]["gameModeStats"]

    # 🔥 SOMENTE SQUAD NORMAL TPP
    stats = game_modes.get("squad")

    return stats

# =============================
# ATUALIZAR DADOS
# =============================
if st.button("🔄 Atualizar Dados"):

    season_id = get_current_season()

    if not season_id:
        st.stop()

    with engine.connect() as conn:

        players = conn.execute(text("SELECT id, nick FROM ranking_squad")).fetchall()

        for player in players:

            player_id_api = get_player_id(player.nick)

            if not player_id_api:
                continue

            stats = get_squad_stats(player_id_api, season_id)

            if not stats:
                continue

            partidas = stats.get("roundsPlayed", 0)
            vitorias = stats.get("wins", 0)
            kills = stats.get("kills", 0)
            assists = stats.get("assists", 0)
            dano = stats.get("damageDealt", 0)
            headshots = stats.get("headshotKills", 0)
            revives = stats.get("revives", 0)
            longest_kill = stats.get("longestKill", 0)

            kd = round(kills / partidas, 2) if partidas > 0 else 0
            dano_medio = round(dano / partidas, 2) if partidas > 0 else 0

            score = round(
                (kills * 2) +
                (assists * 1.5) +
                (vitorias * 5) +
                (dano_medio * 0.01) +
                (headshots * 1.5) +
                (revives * 1.2),
                2
            )

            conn.execute(text("""
                UPDATE ranking_squad
                SET partidas = :partidas,
                    kr = :kd,
                    vitorias = :vitorias,
                    kills = :kills,
                    dano_medio = :dano_medio,
                    assists = :assists,
                    headshots = :headshots,
                    revives = :revives,
                    kill_dist_max = :longest_kill,
                    score = :score
                WHERE id = :id
            """), {
                "partidas": partidas,
                "kd": kd,
                "vitorias": vitorias,
                "kills": kills,
                "dano_medio": dano_medio,
                "assists": assists,
                "headshots": headshots,
                "revives": revives,
                "longest_kill": longest_kill,
                "score": score,
                "id": player.id
            })

        conn.commit()

    st.success("✅ Dados atualizados com sucesso!")

# =============================
# EXIBIR RANKING
# =============================
df = pd.read_sql("""
    SELECT nick, partidas, kr, vitorias, kills,
           dano_medio, assists, headshots,
           revives, kill_dist_max, score
    FROM ranking_squad
    ORDER BY score DESC
""", engine)

st.dataframe(df, use_container_width=True)
