import streamlit as st
import pandas as pd
import requests
import time
from sqlalchemy import text

# =============================
# CONFIGURAÇÃO DA PÁGINA
# =============================
st.set_page_config(
    page_title="PUBG Squad Ranking",
    layout="wide",
    page_icon="🎮"
)

# =============================
# ATUALIZAÇÃO AUTOMÁTICA (SEASON ATUAL)
# =============================
def atualizar_dados_supabase():
    try:
        conn = st.connection(
            "postgresql",
            type="sql",
            url=st.secrets["DATABASE_URL"]
        )

        api_key = st.secrets["PUBG_API_KEY"]

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/vnd.api+json"
        }

        # 🔥 BUSCAR SEASON ATUAL
        season_url = "https://api.pubg.com/shards/steam/seasons"
        r_season = requests.get(season_url, headers=headers)

        seasons = r_season.json()["data"]
        season_id = next(s["id"] for s in seasons if s["attributes"]["isCurrentSeason"])

        # 🔥 BUSCAR JOGADORES DO BANCO
        jogadores = conn.query("SELECT nick FROM ranking_squad", ttl=0)

        for _, row in jogadores.iterrows():
            nick = row["nick"]

            # 🔹 BUSCAR PLAYER ID
            player_url = f"https://api.pubg.com/shards/steam/players?filter[playerNames]={nick}"
            r_player = requests.get(player_url, headers=headers)

            if r_player.status_code != 200 or not r_player.json()["data"]:
                continue

            player_id = r_player.json()["data"][0]["id"]

            # 🔹 BUSCAR STATS DA SEASON ATUAL
            stats_url = f"https://api.pubg.com/shards/steam/players/{player_id}/seasons/{season_id}"
            r_stats = requests.get(stats_url, headers=headers)

            if r_stats.status_code != 200:
                continue

            stats = r_stats.json()["data"]["attributes"]["gameModeStats"].get("squad", {})

            partidas = stats.get("roundsPlayed", 0)
            kills = stats.get("kills", 0)
            assists = stats.get("assists", 0)
            headshots = stats.get("headshotKills", 0)
            revives = stats.get("revives", 0)
            vitorias = stats.get("wins", 0)
            dano_total = stats.get("damageDealt", 0)
            kill_dist_max = stats.get("longestKill", 0)

            kr = kills / partidas if partidas > 0 else 0
            dano_medio = dano_total / partidas if partidas > 0 else 0

            update_sql = text("""
                UPDATE ranking_squad
                SET partidas = :partidas,
                    kills = :kills,
                    assists = :assists,
                    headshots = :headshots,
                    revives = :revives,
                    vitorias = :vitorias,
                    kr = :kr,
                    dano_medio = :dano_medio,
                    kill_dist_max = :kill_dist_max
                WHERE nick = :nick
            """)

            with conn.session as session:
                session.execute(update_sql, {
                    "partidas": partidas,
                    "kills": kills,
                    "assists": assists,
                    "headshots": headshots,
                    "revives": revives,
                    "vitorias": vitorias,
                    "kr": kr,
                    "dano_medio": dano_medio,
                    "kill_dist_max": kill_dist_max,
                    "nick": nick
                })
                session.commit()

            time.sleep(1)

    except Exception as e:
        st.error(f"Erro ao atualizar dados: {e}")


# =============================
# CONEXÃO COM BANCO
# =============================
def get_data():
    try:
        conn = st.connection(
            "postgresql",
            type="sql",
            url=st.secrets["DATABASE_URL"]
        )

        query = "SELECT * FROM ranking_squad"
        df = conn.query(query, ttl=0)
        return df

    except Exception as e:
        st.error(f"Erro na conexão com o banco: {e}")
        return pd.DataFrame()


# =============================
# INTERFACE
# =============================
st.markdown("# 🎮 Ranking Squad - Season Atual")
st.markdown("---")

st.cache_data.clear()

# 🔥 ATUALIZA AO CARREGAR
with st.spinner("Atualizando dados da Season atual..."):
    atualizar_dados_supabase()

df_bruto = get_data()

# =============================
# RESTO DO SEU CÓDIGO ORIGINAL (INALTERADO)
# =============================
