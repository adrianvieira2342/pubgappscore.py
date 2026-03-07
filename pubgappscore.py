import streamlit as st
import pandas as pd
import requests

# =============================
# CONFIGURAÇÃO DA PÁGINA
# =============================
st.set_page_config(
    page_title="PUBG Squad Ranking",
    layout="wide",
    page_icon="🏆",
    initial_sidebar_state="collapsed"
)

# =============================
# FUNÇÃO TELEGRAM
# =============================
def enviar_telegram(nick):
    token = "SEU_TOKEN_AQUI" # Substitua pelo token do BotFather
    chat_id = "SEU_CHAT_ID_AQUI" # Substitua pelo seu ID
    mensagem = f"🚀 **Nova Solicitação de Ranking!**\n\nNickname: `{nick}`"
    url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={mensagem}&parse_mode=Markdown"
    try:
        requests.get(url)
    except:
        pass

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
    [data-testid="stMetricLabel"] * { font-size: 40px !important; }
    [data-testid="stMetricValue"] { font-size: 38px !important; }
    div[data-testid="stTabs"] button { font-size: 16px; font-weight: bold; }
    /* Ajuste para remover bordas extras do dataframe */
    .stDataFrame { width: 100%; }
</style>
""", unsafe_allow_html=True)

# =============================
# CONEXÃO COM BANCO
# =============================
def get_data(table_name="v_ranking_squad_completo"):
    try:
        conn = st.connection("postgresql", type="sql", url=st.secrets["DATABASE_URL"])
        query = f"SELECT * FROM {table_name}"
        return conn.query(query, ttl=0)
    except Exception as e:
        st.error(f"Erro na conexão com o banco: {e}")
        return pd.DataFrame()

# =============================
# PROCESSAMENTO DO RANKING
# =============================
def processar_ranking_completo(df_ranking, col_score):
    total = len(df_ranking)
    novos_nicks, zonas = [], []
    is_bot_ranking = col_score == 'score'
    df_ranking = df_ranking.sort_values(by=col_score, ascending=is_bot_ranking).reset_index(drop=True)

    for i, row in df_ranking.iterrows():
        pos = i + 1
        nick_limpo = str(row['nick']).replace("💀", "").replace("💩", "").replace("👤", "").strip()
        if pos <= 3:
            novos_nicks.append(f"💀 {nick_limpo}"); zonas.append("Elite Zone")
        elif pos > (total - 3):
            novos_nicks.append(f"💩 {nick_limpo}"); zonas.append("Cocô Zone")
        else:
            novos_nicks.append(f"👤 {nick_limpo}"); zonas.append("Medíocre Zone")

    df_ranking['Pos'] = range(1, total + 1)
    df_ranking['nick'], df_ranking['Classificação'] = novos_nicks, zonas
    cols_base = ['Pos', 'Classificação', 'nick', 'partidas', 'kr', 'vitorias', 'kills', 'assists', 'headshots', 'revives', 'kill_dist_max', 'dano_medio']
    if col_score not in cols_base: cols_base.append(col_score)
    return df_ranking[cols_base]

# =============================
# INTERFACE PRINCIPAL
# =============================
st.markdown("<h1 style='text-align:left;'>🏆 PUBG Ranking Squad - Season 40</h1>", unsafe_allow_html=True)

df_bruto = get_data("v_ranking_squad_completo")
df_bots_raw = get_data("ranking_bot")

if not df_bruto.empty:
    if 'ultima_atualizacao' in df_bruto.columns:
        try:
            dt_raw = pd.to_datetime(df_bruto['ultima_atualizacao'].iloc[0])
            st.markdown(f"<p style='text-align:left; color: #888; margin-top: -15px;'>📅 Última atualização: <b>{dt_raw.strftime('%d/%m/%Y %H:%M')}</b></p>", unsafe_allow_html=True)
        except: pass

    st.markdown("---")

    # Lógica de Subtração (Anti-Casual)
    cols_calc = ['partidas', 'vitorias', 'kills', 'assists', 'headshots', 'revives', 'dano_medio']
    for col in cols_calc:
        df_bruto[col] = pd.to_numeric(df_bruto[col], errors='coerce').fillna(0)
        if not df_bots_raw.empty and col in df_bots_raw.columns:
            df_bots_raw[col] = pd.to_numeric(df_bots_raw[col], errors='coerce').fillna(0)

    if not df_bots_raw.empty:
        for _, row_bot in df_bots_raw.iterrows():
            nick_bot = row_bot['nick']
            if nick_bot in df_bruto['nick'].values:
                for col in ['partidas', 'vitorias', 'kills', 'assists', 'headshots', 'revives']:
                    v_total = df_bruto.loc[df_bruto['nick'] == nick_bot, col].values[0]
                    df_bruto.loc[df_bruto['nick'] == nick_bot, col] = max(0, v_total - abs(row_bot[col]))
                p_limpas = max(1, df_bruto.loc[df_bruto['nick'] == nick_bot, 'partidas'].values[0])
                df_bruto.loc[df_bruto['nick'] == nick_bot, 'kr'] = df_bruto.loc[df_bruto['nick'] == nick_bot, 'kills'].values[0] / p_limpas

    for col in cols_calc: df_bruto[col] = df_bruto[col].astype(int)

    def highlight_zones(row):
        if row['Classificação'] == "Elite Zone": return ['background-color: #003300; color: white; font-weight: bold'] * len(row)
        if row['Classificação'] == "Cocô Zone": return ['background-color: #4d0000; color: white; font-weight: bold'] * len(row)
        return [''] * len(row)

    def renderizar_ranking(df_local, col_score, formula, explicacao):
        if formula is not None: df_local[col_score] = formula.round(2)
        ranking_final = processar_ranking_completo(df_local, col_score)

        top1, top2, top3 = st.columns(3)
        for i, card in enumerate([top1, top2, top3]):
            if len(ranking_final) > i:
                with card: st.metric(f"{i+1}º Lugar", ranking_final.iloc[i]['nick'], f"{ranking_final.iloc[i][col_score]:.2f} pts")

        st.markdown(f"<div style='background-color: #161b22; padding: 12px; border-radius: 8px; border-left: 5px solid #0078ff; margin-bottom: 20px;'>💡 {explicacao}</div>", unsafe_allow_html=True)

        if col_score == 'score':
            format_dict = {c: (lambda x: f"- {abs(x):.2f}" if 'kr' in c or 'dist' in c else f"- {int(abs(x))}") for c in cols_calc + ['kr', 'kill_dist_max']}
            format_dict[col_score] = "{:.2f}"
        else:
            format_dict = {c: "{:d}" for c in cols_calc}
            format_dict.update({'kr': "{:.2f}", 'kill_dist_max': "{:.2f}", col_score: "{:.2f}"})

        # REMOVIDO O 'HEIGHT' PARA ELIMINAR O SCROLL E MOSTRAR TODOS OS PLAYERS
        st.dataframe(
            ranking_final.style
            .background_gradient(cmap='YlGnBu' if col_score != 'score' else 'RdYlGn', subset=[col_score])
            .apply(highlight_zones, axis=1)
            .format(format_dict),
            use_container_width=True, hide_index=True,
            column_config={"nick": "Nickname", "partidas": "Partidas", "kr": "K/R", "vitorias": "Vitórias", "kills": "Kills", "assists": "Assists", "headshots": "Headshots", "revives": "Revives", "kill_dist_max": "Kill Dist Máx", "dano_medio": "Dano Médio", "score": "Penalidade", "Score_Pro": "Score Pro", "Score_Team": "Score Team", "Score_Elite": "Score Elite"}
        )

    tab1, tab2, tab3, tab4 = st.tabs(["🔥 PRO Player", "🤝 TEAM Player", "🎯 Atirador de Elite", "🤖 Bot Detector"])
    df_valid = df_bruto[df_bruto['partidas'] > 0].copy()
    p_calc = df_valid['partidas'].replace(0, 1)

    with tab1: renderizar_ranking(df_valid.copy(), 'Score_Pro', (df_valid['kr']*40)+(df_valid['dano_medio']/8)+((df_valid['vitorias']/p_calc)*500), "Fórmula PRO Player")
    with tab2: renderizar_ranking(df_valid.copy(), 'Score_Team', ((df_valid['vitorias']/p_calc)*1000)+((df_valid['revives']/p_calc)*50)+((df_valid['assists']/p_calc)*35), "Fórmula TEAM Player")
    with tab3: renderizar_ranking(df_valid.copy(), 'Score_Elite', (df_valid['kr']*50)+((df_valid['headshots']/p_calc)*60)+(df_valid['dano_medio']/5), "Fórmula ELITE Player")
    with tab4: 
        if not df_bots_raw.empty:
            renderizar_ranking(df_bots_raw[df_bots_raw['partidas']>0].copy(), 'score', None, "Anti-Casual: Penalidades registradas.")

    # --- RODAPÉ DISCRETO ---
    st.markdown("---")
    with st.expander("📝 Solicitar inclusão no Ranking"):
        col_f, col_i = st.columns([1, 1])
        with col_f:
            with st.form("form_adesao", clear_on_submit=True):
                n_nick = st.text_input("Nickname PUBG")
                if st.form_submit_button("Enviar Solicitação") and n_nick:
                    try:
                        with get_data().session as s: # Aproveita a conexão existente
                            s.execute("INSERT INTO jogadores_monitorados (nick, status) VALUES (:n, 'pendente') ON CONFLICT DO NOTHING", {"n": n_nick})
                            s.commit()
                        enviar_telegram(n_nick)
                        st.success("Enviado! O admin foi notificado.")
                    except: st.error("Erro ao salvar no banco.")
        with col_i:
            st.markdown("<small style='color: gray;'>A análise de novos players é feita manualmente pelo administrador.</small>", unsafe_allow_html=True)

    st.markdown("<div style='text-align: center; color: gray; padding: 20px;'>📊 <b>By Adriano Vieira</b></div>", unsafe_allow_html=True)
else:
    st.warning("Conectado ao banco. Aguardando dados...")
