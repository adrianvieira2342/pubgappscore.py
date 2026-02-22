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
# ATUALIZAÇÃO AUTOMÁTICA (SEASON 40 - SQUAD TPP)
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

        # 🔥 BUSCAR TODAS AS SEASONS
        season_url = "https://api.pubg.com/shards/steam/seasons"
        r_season = requests.get(season_url, headers=headers)

        if r_season.status_code != 200:
            st.error("Erro ao buscar seasons")
            return

        seasons = r_season.json()["data"]

        # 🔥 FILTRAR SEASON 40
        season_id = next(
            s["id"] for s in seasons if "40" in s["id"]
        )

        # 🔥 BUSCAR JOGADORES NO BANCO
        jogadores = conn.query("SELECT nick FROM ranking_squad", ttl=0)

        for _, row in jogadores.iterrows():
            nick = row["nick"]

            # BUSCAR PLAYER ID
            player_url = f"https://api.pubg.com/shards/steam/players?filter[playerNames]={nick}"
            r_player = requests.get(player_url, headers=headers)

            if r_player.status_code != 200 or not r_player.json()["data"]:
                continue

            player_id = r_player.json()["data"][0]["id"]

            # BUSCAR STATS DA SEASON 40
            stats_url = f"https://api.pubg.com/shards/steam/players/{player_id}/seasons/{season_id}"
            r_stats = requests.get(stats_url, headers=headers)

            if r_stats.status_code != 200:
                continue

            stats_json = r_stats.json()
            game_modes = stats_json["data"]["attributes"]["gameModeStats"]

            # 🔥 APENAS SQUAD (TPP)
            if "squad" not in game_modes:
                continue

            stats = game_modes["squad"]

            partidas = stats.get("roundsPlayed", 0)
            if partidas == 0:
                continue

            kills = stats.get("kills", 0)
            assists = stats.get("assists", 0)
            headshots = stats.get("headshotKills", 0)
            revives = stats.get("revives", 0)
            vitorias = stats.get("wins", 0)
            dano_total = stats.get("damageDealt", 0)
            kill_dist_max = stats.get("longestKill", 0)

            kr = kills / partidas
            dano_medio = dano_total / partidas

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
        return conn.query(query, ttl=0)

    except Exception as e:
        st.error(f"Erro na conexão com o banco: {e}")
        return pd.DataFrame()


# =============================
# PROCESSAMENTO DO RANKING
# =============================
def processar_ranking_completo(df_ranking, col_score):
    total = len(df_ranking)
    novos_nicks = []
    zonas = []
    posicoes = []

    df_ranking = df_ranking.reset_index(drop=True)

    for i, row in df_ranking.iterrows():
        pos = i + 1
        nick_limpo = str(row['nick'])

        for emoji in ["💀", "💩", "👤", "🏅"]:
            nick_limpo = nick_limpo.replace(emoji, "").strip()

        posicoes.append(pos)

        if pos <= 3:
            novos_nicks.append(f"💀 {nick_limpo}")
            zonas.append("Elite Zone")
        elif pos > (total - 3):
            novos_nicks.append(f"💩 {nick_limpo}")
            zonas.append("Cocô Zone")
        else:
            novos_nicks.append(f"👤 {nick_limpo}")
            zonas.append("Medíocre Zone")

    df_ranking['Pos'] = posicoes
    df_ranking['nick'] = novos_nicks
    df_ranking['Classificação'] = zonas

    cols_base = [
        'Pos', 'Classificação', 'nick',
        'partidas', 'kr', 'vitorias',
        'kills', 'assists', 'headshots',
        'revives', 'kill_dist_max', 'dano_medio'
    ]

    return df_ranking[cols_base + [col_score]]


# =============================
# INTERFACE
# =============================
st.markdown("# 🎮 Ranking Squad - Season 40")
st.markdown("---")

with st.spinner("Atualizando dados da Season 40..."):
    atualizar_dados_supabase()

df_bruto = get_data()

if not df_bruto.empty:

    df_bruto['partidas'] = df_bruto['partidas'].replace(0, 1)

    tab1, tab2, tab3 = st.tabs([
        "🔥 PRO (Equilibrado)",
        "🤝 TEAM (Suporte)",
        "🎯 ELITE (Skill)"
    ])

    def renderizar_ranking(df_local, col_score, formula):

        df_local[col_score] = formula.round(2)
        ranking_ordenado = df_local.sort_values(
            col_score,
            ascending=False
        ).reset_index(drop=True)

        ranking_final = processar_ranking_completo(
            ranking_ordenado,
            col_score
        )

        st.dataframe(
            ranking_final.style
            .background_gradient(cmap='YlGnBu', subset=[col_score])
            .format(precision=2),
            use_container_width=True,
            height=650,
            hide_index=True
        )

    with tab1:
        f_pro = (
            (df_bruto['kr'] * 40)
            + (df_bruto['dano_medio'] / 8)
            + ((df_bruto['vitorias'] / df_bruto['partidas']) * 100 * 5)
        )
        renderizar_ranking(df_bruto.copy(), 'Score_Pro', f_pro)

    with tab2:
        f_team = (
            ((df_bruto['vitorias'] / df_bruto['partidas']) * 100 * 10)
            + ((df_bruto['revives'] / df_bruto['partidas']) * 50)
            + ((df_bruto['assists'] / df_bruto['partidas']) * 35)
        )
        renderizar_ranking(df_bruto.copy(), 'Score_Team', f_team)

    with tab3:
        f_elite = (
            (df_bruto['kr'] * 50)
            + ((df_bruto['headshots'] / df_bruto['partidas']) * 60)
            + (df_bruto['dano_medio'] / 5)
        )
        renderizar_ranking(df_bruto.copy(), 'Score_Elite', f_elite)

else:
    st.warning("Nenhum dado encontrado na tabela ranking_squad.")
