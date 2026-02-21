import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import time

# =============================
# CONEXÃO LIMPA COM O BANCO
# =============================
def get_data_fresh():
    try:
        # Pega a URL que você salvou corretamente agora no TOML
        db_url = st.secrets["DATABASE_URL"]
        
        # isolation_level="AUTOCOMMIT" é essencial para o Transaction Pooler (6543)
        engine = create_engine(
            db_url, 
            pool_pre_ping=True,
            execution_options={"isolation_level": "AUTOCOMMIT"}
        )
        
        with engine.connect() as conn:
            # Query com Cache Buster (comentário com tempo atual) para forçar dados novos
            query = text(f"SELECT * FROM ranking_squad -- refresh_{int(time.time())}")
            df = pd.read_sql(query, conn)
            return df
    except Exception as e:
        st.error(f"Erro ao buscar dados: {e}")
        return pd.DataFrame()

# No seu layout original:
st.title("🎮 Ranking Squad - Season 40")

if st.button("🔄 Sincronizar Agora"):
    st.cache_data.clear()
    st.cache_resource.clear()
    st.rerun()

df_bruto = get_data_fresh()

if not df_bruto.empty:
    st.success(f"Dados carregados com sucesso! ({len(df_bruto)} jogadores encontrados)")
    # Continue com seu código de abas e cálculos aqui...
else:
    st.info("O banco conectou, mas a tabela 'ranking_squad' parece estar vazia.")
