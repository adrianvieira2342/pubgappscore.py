import streamlit as st
import pandas as pd

# =============================
# CONFIGURAÇÃO DA PÁGINA (ORIGINAL)
# =============================
st.set_page_config(
    page_title="PUBG Squad Ranking",
    layout="wide",
    page_icon="🏆",
    initial_sidebar_state="collapsed"
)

# =============================
# CSS TEMA ESCURO CUSTOM (ORIGINAL)
# =============================
st.markdown("""
<style>
    .stApp {
        background-color: #0e1117;
        color: white;
    }
    div[data-testid="stMetric"] {
        background-color: #161b22;
        padding: 15px;
        border-radius: 12px;
        border: 1px solid #30363d;
        text-align: center;
    }
    [data-testid="stMetricLabel"] * {
        font-size: 40px !important;
    }
    [data-testid="stMetricValue"] {
        font-size: 38px !important;
    }
    div[data-testid="stTabs"] button {
        font-size: 16px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# =============================
# CONEXÃO COM BANCO (AJUSTADA PARA ACEITAR TABELA)
# =============================
def get_data(table_name="v_ranking_squad_completo"):
    try:
        conn = st.connection(
            "postgresql",
            type="sql",
            url=st.secrets["DATABASE_URL"]
        )
        query = f"SELECT * FROM {table_name}"
        df = conn.query(query, ttl=0) 
        return df
    except Exception as e:
        st.error(f"Erro na conexão com o banco: {e}")
        return pd.DataFrame()

# =============================
# PROCESSAMENTO DO RANKING (ORIGINAL)
# =============================
def processar_ranking_completo(df_ranking, col_score):
    total = len(df_ranking)
    novos_nicks = []
    zonas = []
    
    # Para a aba de bots (score negativo), ordenamos de forma crescente (menores scores no topo)
    is_bot_ranking = col_score == 'score'
    df_ranking = df_ranking.sort_values(by=col_score, ascending=is_bot_ranking).reset_index(drop=True)

    for i, row in df_ranking.iterrows():
        pos = i + 1
        nick_limpo = str(row['nick'])
        for emoji in ["💀", "💩", "👤"]:
            nick_limpo = nick_limpo.replace(emoji, "").strip()

        if pos <= 3:
            novos_nicks.append(f"💀 {nick_limpo}")
            zonas.append("Elite Zone")
        elif pos > (total - 3):
            novos_nicks.append(f"💩 {nick_limpo}")
            zonas.append("Cocô Zone")
        else:
            novos_nicks.append(f"👤 {nick_limpo}")
            zonas.append("Medíocre Zone")

    df_ranking['Pos'] = range(1, total + 1)
    df_ranking['nick'] = novos_nicks
    df_ranking['Classificação'] = zonas

    cols_base = [
        'Pos', 'Classificação', 'nick',
        'partidas', 'kr', 'vitorias',
        'kills', 'assists', 'headshots',
        'revives', 'kill_dist_max', 'dano_medio'
    ]
    
    if col_score not in cols_base:
        cols_base.append(col_score)
        
    return df_ranking[cols_base]

# =============================
# INTERFACE
# =============================
st.markdown("<h1 style='text-align:left;'>🏆 PUBG Ranking Squad - Season 40</h1>", unsafe_allow_html=True)

df_bruto = get_data("v_ranking_squad_completo")
df_bots_raw = get_data("ranking_bot") # Nova fonte de dados

if not df_bruto.empty:
    # --- INFORMATIVO DE ATUALIZAÇÃO ---
    if 'ultima_atualizacao' in df_bruto.columns:
        try:
            dt_raw = pd.to_datetime(df_bruto['ultima_atualizacao'].iloc[0])
            dt_formatada = dt_raw.strftime('%d/%m/%Y %H:%M')
            st.markdown(f"<p style='text-align:left; color: #888; margin-top: -15px;'>📅 Última atualização do banco: <b>{dt_formatada}</b></p>", unsafe_allow_html=True)
        except: pass

    st.markdown("---")

    # Conversão numérica protegida
    cols_inteiras = ['partidas', 'vitorias', 'kills', 'assists', 'headshots', 'revives', 'dano_medio']
    for col in cols_inteiras:
        if col in df_bruto.columns:
            df_bruto[col] = pd.to_numeric(df_bruto[col], errors='coerce').fillna(0).astype(int)
        if not df_bots_raw.empty and col in df_bots_raw.columns:
            df_bots_raw[col] = pd.to_numeric(df_bots_raw[col], errors='coerce').fillna(0).astype(int)

    # --- FUNÇÕES DE SUPORTE À UI (ORIGINAL) ---
    def highlight_zones(row):
        if row['Classificação'] == "Elite Zone":
            return ['background-color: #003300; color: white; font-weight: bold'] * len(row)
        if row['Classificação'] == "Cocô Zone":
            return ['background-color: #4d0000; color: white; font-weight: bold'] * len(row)
        return [''] * len(row)

    def renderizar_ranking(df_local, col_score, formula, explicacao):
        if formula is not None:
            df_local[col_score] = formula.round(2)
        
        ranking_final = processar_ranking_completo(df_local, col_score)

        top1, top2, top3 = st.columns(3)
        with top1: st.metric("🥇 1º Lugar", ranking_final.iloc[0]['nick'] if len(ranking_final) > 0 else "-", f"{ranking_final.iloc[0][col_score]:.2f} pts")
        with top2: st.metric("🥈 2º Lugar", ranking_final.iloc[1]['nick'] if len(ranking_final) > 1 else "-", f"{ranking_final.iloc[1][col_score]:.2f} pts")
        with top3: st.metric("🥉 3º Lugar", ranking_final.iloc[2]['nick'] if len(ranking_final) > 2 else "-", f"{ranking_final.iloc[2][col_score]:.2f} pts")

        st.markdown(f"<div style='background-color: #161b22; padding: 12px; border-radius: 8px; border-left: 5px solid #0078ff; margin-bottom: 20px; text-align: left;'>💡 {explicacao}</div>", unsafe_allow_html=True)

        format_dict = {
            'kr': "{:.2f}", 'kill_dist_max': "{:.2f}", col_score: "{:.2f}",
            'partidas': "{:d}", 'vitorias': "{:d}", 'kills': "{:d}", 
            'assists': "{:d}", 'headshots': "{:d}", 'revives': "{:d}", 'dano_medio': "{:d}"
        }
        
        st.dataframe(
            ranking_final.style
            .background_gradient(cmap='YlGnBu' if col_score != 'score' else 'RdYlGn', subset=[col_score])
            .apply(highlight_zones, axis=1)
            .format(format_dict),
            use_container_width=True,
            height=(len(ranking_final) * 35) + 80,
            hide_index=True,
            column_config={
                "nick": "Nickname", "partidas": "Partidas", "kr": "K/R",
                "vitorias": "Vitórias", "kills": "Kills", "assists": "Assists",
                "headshots": "Headshots", "revives": "Revives",
                "kill_dist_max": "Kill Dist Máx", "dano_medio": "Dano Médio",
                "Score_Pro": "Score Pro", "Score_Team": "Score Team", 
                "Score_Elite": "Score Elite", "score": "Penalidade"
            }
        )

    # --- TABS (INCLUINDO A NOVA TAB) ---
    tab1, tab2, tab3, tab4 = st.tabs([
        "🔥 PRO Player", 
        "🤝 TEAM Player", 
        "🎯 Atirador de Elite",
        "🤖 Anti-Casual (Bots)"
    ])

    df_valid = df_bruto[df_bruto['partidas'] > 0].copy()
    df_valid['partidas_calc'] = df_valid['partidas'].replace(0, 1)

    with tab1:
        f_pro = (df_valid['kr'] * 40) + (df_valid['dano_medio'] / 8) + ((df_valid['vitorias'] / df_valid['partidas_calc']) * 500)
        renderizar_ranking(df_valid.copy(), 'Score_Pro', f_pro, "Fórmula PRO: Valoriza o equilíbrio entre sobrevivência e agressividade.")

    with tab2:
        f_team = ((df_valid['vitorias'] / df_valid['partidas_calc']) * 1000) + ((df_valid['revives'] / df_valid['partidas_calc']) * 50) + ((df_valid['assists'] / df_valid['partidas_calc']) * 35)
        renderizar_ranking(df_valid.copy(), 'Score_Team', f_team, "Fórmula TEAM: Foco total no jogo coletivo.")

    with tab3:
        f_elite = (df_valid['kr'] * 50) + ((df_valid['headshots'] / df_valid['partidas_calc']) * 60) + (df_valid['dano_medio'] / 5)
        renderizar_ranking(df_valid.copy(), 'Score_Elite', f_elite, "Fórmula ELITE: Prioriza K/R, precisão de Headshots e volume de dano.")

    with tab4:
        if not df_bots_raw.empty:
            # Filtramos quem tem score (penalidade) ou partidas de bot
            df_bots = df_bots_raw[df_bots_raw['partidas'] > 0].copy()
            if not df_bots.empty:
                renderizar_ranking(df_bots, 'score', None, "Anti-Casual: Jogadores penalizados por abater bots em partidas casuais. Quanto menor o score, maior a penalidade.")
            else:
                st.info("Nenhuma penalidade registrada.")

    st.markdown("---")
    st.markdown("<div style='text-align: center; color: gray; padding: 20px;'>📊 <b>By Adriano Vieira</b></div>", unsafe_allow_html=True)

else:
    st.warning("Conectado ao banco. Aguardando dados...")
