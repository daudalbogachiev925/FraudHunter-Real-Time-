import os, requests, pandas as pd, streamlit as st
import plotly.express as px

API = os.getenv("API_URL", "http://localhost:8000")
st.set_page_config(page_title="FraudHunter", layout="wide")
st.title("🛡 FraudHunter — real-time детекция")

tab1, tab2, tab3 = st.tabs(["📊 Обзор", "🚨 Алерты", "👤 По пользователю"])

with tab1:
    stats = requests.get(f"{API}/stats").json()
    c1, c2, c3 = st.columns(3)
    c1.metric("Транзакций", stats["total"])
    c2.metric("Фродов", stats["frauds"])
    c3.metric("Avg probability", f"{stats['avg_probability']:.3f}")

with tab2:
    min_p = st.slider("Мин. вероятность", 0.3, 0.99, 0.6)
    alerts = requests.get(f"{API}/alerts", params={"limit": 100, "min_p": min_p}).json()
    if alerts:
        df = pd.DataFrame(alerts)
        st.dataframe(df, use_container_width=True)
        fig = px.histogram(df, x="amount", nbins=30, title="Распределение сумм фродов")
        st.plotly_chart(fig, use_container_width=True)

with tab3:
    uid = st.number_input("user_id", 1, 100000, 42)
    if st.button("Показать"):
        st.json(requests.get(f"{API}/user/{uid}").json())
