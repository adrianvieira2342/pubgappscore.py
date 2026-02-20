import streamlit as st
import pandas as pd

# Configuração da página
st.set_page_config(page_title="PUBG Squad Ranking", layout="wide", page_icon="🎮")

def get_data():
    try:
        # Conexão nativa do Streamlit para PostgreSQL (Supabase)
        conn = st.connection("postgresql", type="sql")
        # Busca os dados da tabela ranking_squad
        query = "SELECT * FROM ranking_squad"
        df = conn.query(query, ttl="5m")
        return df
    except Exception as e:
        st.error(f"Erro na conexão com o banco: {e}")
        return pd.DataFrame()

def processar_ranking_completo(df_ranking, col_score):
    total = len(df_ranking)
    novos_nicks, zonas, posicoes = [], [], []
    
    df_ranking = df_ranking.reset_index(drop=True)
    
    for i, row in df_ranking.iterrows():
        pos = i + 1
        nick_limpo = str(row['nick'])
        for e in ["💀", "💩", "👤", "🏅"]:
            nick_limpo = nick_limpo.replace(e, "").strip()
        
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
    
    cols_base = ['Pos', 'Classificação', 'nick', 'partidas', 'kr', 'vitorias', 'kills', 'assists', 'headshots', 'revives', 'kill_dist_max', 'dano_medio']
    return df_ranking[cols_base + [col_score]]

# --- INTERFACE ---
st.markdown("# 🎮 Ranking Squad - Season 40")
st.markdown("---")

df_bruto = get_data()

if not df_bruto.empty:
    tab1, tab2, tab3 = st.tabs(["🔥 PRO", "🤝 TEAM", "🎯 ELITE"])

    def renderizar_ranking(df_local, col_score, formula):
        df_local[col_score] = formula.round(2)
        ranking_ordenado = df_local.sort_values(col_score, ascending=False).reset_index(drop=True)
        
        top1, top2, top3 = st.columns(3)
        with top1: st.metric("🥇 1º", ranking_ordenado.iloc[0]['nick'], f"{ranking_ordenado.iloc[0][col_score]} pts")
        with top2: st.metric("🥈 2º", ranking_ordenado.iloc[1]['nick'], f"{ranking_ordenado.iloc[1][col_score]} pts")
        with top3: st.metric("🥉 3º", ranking_ordenado.iloc[2]['nick'], f"{ranking_ordenado.iloc[2][col_score]} pts")
        
        st.markdown("---")
        ranking_final = processar_ranking_completo(ranking_ordenado, col_score)
        
        def highlight_zones(row):
            if row['Classificação'] == "Elite Zone": return ['background-color: #004d00; color: white'] * len(row)
            if row['Classificação'] == "Cocô Zone": return ['background-color: #4d2600; color: white'] * len(row)
            return [''] * len(row)

        st.dataframe(ranking_final.style.apply(highlight_zones, axis=1).format(precision=2), use_container_width=True, height=600, hide_index=True)

    with tab1:
        f_pro = ((df_bruto['kr'] * 40) + (df_bruto['dano_medio'] / 8) + ((df_bruto['vitorias'] / df_bruto['partidas']) * 500))
        renderizar_ranking(df_bruto.copy(), 'Score_Pro', f_pro)
    # ... (as outras abas seguem a mesma lógica)

else:
    st.warning("Banco conectado, mas sem dados para exibir.")
