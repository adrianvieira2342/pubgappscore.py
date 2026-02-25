import streamlit as st
import pandas as pd
from datetime import datetime
import pytz

# =============================
# CONFIGURAÇÃO DA PÁGINA
# =============================
st.set_page_config(
    page_title="PUBG Squad Ranking",
    layout="wide",
    page_icon="🎮",
    initial_sidebar_state="collapsed"
)

# =============================
# CSS TEMA ESCURO CUSTOM
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
    div[data-testid="stTabs"] button {
        font-size: 16px;
        font-weight: bold;
    }
    .sync-bar {
        background-color: #1a7f37;
        color: white;
        padding: 10px;
        border-radius: 20px;
        text-align: center;
        font-weight: bold;
        margin-bottom: 20px;
        font-size: 14px;
    }
</style>
""", unsafe_allow_html=True)

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
# PROCESSAMENTO DO RANKING
# =============================
def processar_ranking_completo(df_ranking, col_score):
    total = len(df_ranking)
    novos_nicks = []
    zonas = []
    
    df_ranking = df_ranking.sort_values(by=col_score, ascending=False).reset_index(drop=True)

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
st.markdown("<h1 style='text-align:center;'>🎮 Ranking Squad - Season 40</h1>", unsafe_allow_html=True)

df_bruto = get_data()

if not df_bruto.empty:
    
    # --- LOGICA DE SINCRONIZAÇÃO (CORREÇÃO DO HORÁRIO) ---
    try:
        # Pega a data mais recente da coluna 'atualizado_em'
        ultima_sinc = pd.to_datetime(df_bruto['atualizado_em']).max()
        
        # Se a data vier do banco como UTC (fuso zero), convertemos para Brasília
        if ultima_sinc.tzinfo is None:
            ultima_sinc = ultima_sinc.tz_localize('UTC')
        
        fuso_br = pytz.timezone('America/Sao_Paulo')
        ultima_sinc_br = ultima_sinc.astimezone(fuso_br)
        data_formatada = ultima_sinc_br.strftime('%d/%m/%Y %H:%M:%S')
    except:
        data_formatada = "--/--/---- --:--:--"

    # Exibe a tarja verde com o horário REAL do banco
    st.markdown(f"""
        <div class="sync-bar">
            ● Dados Sincronizados (Brasília): {data_formatada}
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")

    cols_inteiras = ['partidas', 'vitorias', 'kills', 'assists', 'headshots', 'revives', 'dano_medio']
    for col in cols_inteiras:
        df_bruto[col] = pd.to_numeric(df_bruto[col], errors='coerce').fillna(0).astype(int)
    
    # Filtra apenas jogadores com 1 ou mais partidas
    df_bruto = df_bruto[df_bruto['partidas'] > 0].copy()
    
    if df_bruto.empty:
        st.info("Nenhum jogador possui partidas registradas nesta temporada.")
    else:
        df_bruto['partidas_calc'] = df_bruto['partidas'].replace(0, 1)

        tab1, tab2, tab3 = st.tabs([
            "🔥 PRO (Equilibrado)", 
            "🤝 TEAM (Suporte)", 
            "🎯 ELITE (Skill)"
        ])

        def highlight_zones(row):
            if row['Classificação'] == "Elite Zone":
                return ['background-color: #003300; color: white; font-weight: bold'] * len(row)
            if row['Classificação'] == "Cocô Zone":
                return ['background-color: #4d0000; color: white; font-weight: bold'] * len(row)
            return [''] * len(row)

        def renderizar_ranking(df_local, col_score, formula):
            df_local[col_score] = formula.round(2)
            ranking_final = processar_ranking_completo(df_local, col_score)

            top1, top2, top3 = st.columns(3)
            with top1:
                st.metric("🥇 1º Lugar", ranking_final.iloc[0]['nick'] if len(ranking_final) > 0 else "-", f"{ranking_final.iloc[0][col_score] if len(ranking_final) > 0 else 0} pts")
            with top2:
                st.metric("🥈 2º Lugar", ranking_final.iloc[1]['nick'] if len(ranking_final) > 1 else "-", f"{ranking_final.iloc[1][col_score] if len(ranking_final) > 1 else 0} pts")
            with top3:
                st.metric("🥉 3º Lugar", ranking_final.iloc[2]['nick'] if len(ranking_final) > 2 else "-", f"{ranking_final.iloc[2][col_score] if len(ranking_final) > 2 else 0} pts")

            format_dict = {
                'kr': "{:.2f}", 'kill_dist_max': "{:.2f}", col_score: "{:.2f}",
                'partidas': "{:d}", 'vitorias': "{:d}", 'kills': "{:d}", 
                'assists': "{:d}", 'headshots': "{:d}", 'revives': "{:d}", 'dano_medio': "{:d}"
            }

            altura_dinamica = (len(ranking_final) * 35) + 120

            st.dataframe(
                ranking_final.style
                .background_gradient(cmap='YlGnBu', subset=[col_score])
                .apply(highlight_zones, axis=1)
                .format(format_dict),
                use_container_width=True,
                height=altura_dinamica,
                hide_index=True
            )

        with tab1:
            f_pro = (df_bruto['kr'] * 40) + (df_bruto['dano_medio'] / 8) + ((df_bruto['vitorias'] / df_bruto['partidas_calc']) * 500)
            renderizar_ranking(df_bruto.copy(), 'Score_Pro', f_pro)

        with tab2:
            f_team = ((df_bruto['vitorias'] / df_bruto['partidas_calc']) * 1000) + ((df_bruto['revives'] / df_bruto['partidas_calc']) * 50) + ((df_bruto['assists'] / df_bruto['partidas_calc']) * 35)
            renderizar_ranking(df_bruto.copy(), 'Score_Team', f_team)

        with tab3:
            f_elite = (df_bruto['kr'] * 50) + ((df_bruto['headshots'] / df_bruto['partidas_calc']) * 60) + (df_bruto['dano_medio'] / 5)
            renderizar_ranking(df_bruto.copy(), 'Score_Elite', f_elite)

    st.markdown("---")
    st.markdown("<div style='text-align: center; color: gray; padding: 20px;'>📊 <b>By Adriano Vieira</b></div>", unsafe_allow_html=True)

else:
    st.warning("Conectado ao banco. Aguardando dados...")
