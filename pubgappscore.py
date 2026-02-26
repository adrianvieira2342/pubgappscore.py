import streamlit as st
import pandas as pd

# ... (Mantenha as configurações de página e CSS iguais)

# =============================
# CONEXÃO COM BANCO (ATUALIZADA)
# =============================
def get_data():
    try:
        conn = st.connection(
            "postgresql",
            type="sql",
            url=st.secrets["DATABASE_URL"]
        )
        # Agora consultamos a VIEW que criamos anteriormente
        query = "SELECT * FROM v_ranking_squad_completo"
        df = conn.query(query, ttl=0)
        return df
    except Exception as e:
        st.error(f"Erro na conexão com o banco: {e}")
        return pd.DataFrame()

# ... (Mantenha a função processar_ranking_completo igual)

# =============================
# INTERFACE
# =============================
st.markdown("<h1 style='text-align:center;'>🎮 Ranking Squad - Season 40</h1>", unsafe_allow_html=True)

df_bruto = get_data()

if not df_bruto.empty:
    # EXTRAÇÃO DA DATA DE ATUALIZAÇÃO
    # Como a View repete a data em todas as linhas, pegamos a primeira
    ultima_atualizacao = df_bruto['ultima_atual_br'].iloc[0] if 'ultima_atual_br' in df_bruto.columns else None
    # Caso sua View tenha outro nome para a coluna, ajuste acima para 'ultima_atualizacao'
    
    if ultima_atualizacao:
        # Formata a data para o padrão brasileiro (DD/MM/AAAA HH:MM)
        dt_formatada = pd.to_datetime(ultima_atualizacao).strftime('%d/%m/%Y %H:%M')
        st.markdown(f"<p style='text-align:center; color: #888;'>📅 Última atualização do banco: <b>{dt_formatada}</b></p>", unsafe_allow_html=True)

    st.markdown("---")

    # --- RESTANTE DO SEU PROCESSAMENTO ---
    cols_inteiras = ['partidas', 'vitorias', 'kills', 'assists', 'headshots', 'revives', 'dano_medio']
    for col in cols_inteiras:
        if col in df_bruto.columns: # Garante que a coluna existe
            df_bruto[col] = pd.to_numeric(df_bruto[col], errors='coerce').fillna(0).astype(int)
    
    # ... (Continua o código com tabs e renderização do ranking)
