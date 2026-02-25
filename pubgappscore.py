import streamlit as st
import pandas as pd
import psycopg2

# =============================
# INTERFACE (Trecho atualizado)
# =============================
st.markdown("# 🎮 Ranking Squad - Season 40")
st.markdown("---")

df_bruto = get_data()

if not df_bruto.empty:
    df_bruto['partidas'] = df_bruto['partidas'].replace(0, 1)

    # Adicionando a quarta aba na lista
    tab1, tab2, tab3, tab4 = st.tabs([
        "🔥 PRO (Equilibrado)", 
        "🤝 TEAM (Suporte)", 
        "🎯 ELITE (Skill)",
        "📊 GERAL (Métricas)"
    ])

    # ... (mantenha a função renderizar_ranking e as tabs 1, 2 e 3 como estão)

    # =============================
    # NOVA ABA: GERAL (Métricas)
    # =============================
    with tab4:
        st.subheader("Estatísticas Brutas da Temporada")
        st.info("Nesta aba os jogadores são listados por maior número de abates (Kills) sem fórmulas de score.")
        
        # Ordenação simples por Kills
        df_geral = df_bruto.sort_values(by='kills', ascending=False).reset_index(drop=True)
        
        # Aplicando a mesma formatação visual de zonas
        ranking_geral = processar_ranking_completo(df_geral, 'kills') # Usamos kills como coluna de referência

        st.dataframe(
            ranking_geral.style
            .background_gradient(cmap='Greens', subset=['kills'])
            .apply(highlight_zones, axis=1)
            .format(precision=2),
            use_container_width=True,
            height=650,
            hide_index=True
        )
