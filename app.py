import streamlit as st
import pandas as pd
from analyzer import main, plot_combined_chart

st.title("📊 Покерный анализатор")

if st.button("Запустить анализ"):
    main()
    df = pd.read_csv("poker_stats.csv")
    st.success("Анализ завершён!")
    st.subheader("📊 Статистика")
    st.dataframe(df)

    with open("poker_stats.csv", "rb") as f:
        st.download_button("📥 Скачать CSV", f, file_name="poker_stats.csv")

    st.subheader("📈 График эффективности")
    st.image("combined_ev_chart.png")
