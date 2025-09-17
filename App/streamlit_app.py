import os
import time
import streamlit as st
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://app:app@db:1234/appdb")

@st.cache_resource
def get_engine():
    # Tenta conectar com alguns retries até o Postgres ficar pronto
    for i in range(20):
        try:
            engine = create_engine(DATABASE_URL, pool_pre_ping=True)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return engine
        except Exception as e:
            time.sleep(1 + i * 0.1)
    # Se não conseguiu, levanta erro
    raise RuntimeError("Não foi possível conectar ao Postgres.")

engine = get_engine()

# Garante a tabela (caso init.sql não tenha rodado por algum motivo)
with engine.begin() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS public.submissions (
          id SERIAL PRIMARY KEY,
          name TEXT NOT NULL,
          message TEXT NOT NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """))

st.title("📬 Formulário Streamlit → Postgres")

with st.form("form"):
    name = st.text_input("Seu nome")
    message = st.text_area("Sua mensagem")
    submitted = st.form_submit_button("Enviar")

if submitted:
    if not name or not message:
        st.warning("Preencha nome e mensagem.")
    else:
        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO public.submissions (name, message) VALUES (:n, :m)"),
                {"n": name, "m": message}
            )
        st.success("Registro salvo com sucesso!")

st.divider()
st.subheader("Últimos envios")
limit = st.slider("Quantos registros exibir:", min_value=1, max_value=50, value=10)
with engine.connect() as conn:
    rows = conn.execute(
        text("SELECT id, name, message, created_at FROM public.submissions ORDER BY created_at DESC LIMIT :lim"),
        {"lim": limit}
    ).mappings().all()

if rows:
    st.dataframe(rows, use_container_width=True)
else:
    st.info("Nenhum registro ainda. Envie o primeiro! 🚀")
