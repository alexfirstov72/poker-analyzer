import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from datetime import datetime
from poker_analyzer import PokerHandParser, PokerStatsCalculator  # Импорт анализатора

# Настройки страницы
st.set_page_config(
    page_title="Покерный анализатор", 
    page_icon="♠️",
    layout="wide"
)

# Заголовок приложения
st.title("♠️ Покерный анализатор")
st.markdown("Загрузите файл с историей рук для анализа статистики")

# Функция для создания пустой статистики
def create_empty_stats():
    positions = ["UTG", "UTG+1", "MP", "HJ", "CO", "BTN", "SB", "BB"]
    return pd.DataFrame({
        "Position": positions,
        "EV bb/100": [0] * len(positions),
        "VPIP": [0.0] * len(positions),
        "PFR": [0.0] * len(positions),
        "Hands": [0] * len(positions)
    })

# Загрузка файла
uploaded_file = st.file_uploader(
    "Выберите файл с историей рук (формат TXT)", 
    type=["txt"],
    accept_multiple_files=False
)

# Инициализация статистики
stats_df = create_empty_stats()

# Обработка загруженного файла
if uploaded_file is not None:
    # Сохраняем загруженный файл
    file_name = f"hand_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(file_name, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    st.success(f"Файл {uploaded_file.name} успешно загружен!")
    
    try:
        # Чтение и анализ файла
        with open(file_name, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Парсинг рук
        parser = PokerHandParser()
        parser.parse_file(content)
        
        # Расчет статистики
        calculator = PokerStatsCalculator(parser.hands)
        stats = calculator.calculate_stats()
        
        # Подготовка данных для отображения
        positions = ["UTG", "UTG1", "MP", "HJ", "CO", "BTN", "SB", "BB"]
        data = []
        
        for pos in positions:
            pos_data = stats.get(pos, {})
            data.append({
                "Position": pos.replace("UTG1", "UTG+1"),
                "EV bb/100": pos_data.get("ev_bb_100", 0),
                "VPIP": pos_data.get("vpip", 0),
                "PFR": pos_data.get("pfr", 0),
                "Hands": pos_data.get("hands", 0)
            })
        
        stats_df = pd.DataFrame(data)
        st.success("Анализ завершён!")
        
    except Exception as e:
        st.error(f"Ошибка анализа: {str(e)}")
        stats_df = create_empty_stats()
else:
    st.info("Пожалуйста, загрузите файл с историей рук для анализа")

# Отображение статистики
st.subheader("Статистика по позициям")
st.table(stats_df)

# Кнопка скачивания CSV
csv = stats_df.to_csv(index=False).encode('utf-8')
st.download_button(
    label="Скачать CSV",
    data=csv,
    file_name="poker_stats.csv",
    mime="text/csv"
)

# Создание графика
st.subheader("📈 График эффективности")
fig, ax = plt.subplots(figsize=(10, 6))
positions = stats_df["Position"]

# График EV
ax.bar(positions, stats_df["EV bb/100"], color='skyblue', label='EV bb/100')

# График VPIP/PFR
ax2 = ax.twinx()
ax2.plot(positions, stats_df["VPIP"], 'o-', color='green', label='VPIP')
ax2.plot(positions, stats_df["PFR"], 'o-', color='red', label='PFR')

# Настройки оформления
ax.set_xlabel("Позиция")
ax.set_ylabel("EV (bb/100)")
ax2.set_ylabel("VPIP/PFR (%)")
ax.set_title("Эффективность по позициям")
fig.legend(loc="upper left", bbox_to_anchor=(0.1, 0.9))
plt.tight_layout()

st.pyplot(fig)

# Удаление временного файла
if uploaded_file is not None and os.path.exists(file_name):
    os.remove(file_name)