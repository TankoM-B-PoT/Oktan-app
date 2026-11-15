"""
Веб-приложение для расчета октанового числа с автоидентификацией пиков.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from calculator import OctaneCalculator

st.set_page_config(
    page_title="Расчет октанового числа",
    page_icon="⛽",
    layout="wide",
    initial_sidebar_state="collapsed",
)

CLASS_COLORS = {
    "P": "#2E86AB", "I": "#A23B72", "O": "#F18F01",
    "N": "#C73E1D", "A": "#3B1F2B", "OXY": "#44BBA4",
}
CLASS_NAMES = {
    "P": "Парафины", "I": "Изопарафины", "O": "Олефины",
    "N": "Нафтены", "A": "Ароматика", "OXY": "Кислородсодержащие",
}

GOST_STANDARDS = {
    "АИ-92":  {"RON_min": 92.0,  "MON_min": 82.0, "A_max": 25},
    "АИ-95":  {"RON_min": 95.0,  "MON_min": 85.0, "A_max": 30},
    "АИ-98":  {"RON_min": 98.0,  "MON_min": 88.0, "A_max": 35},
    "АИ-100": {"RON_min": 100.0, "MON_min": 90.0, "A_max": 35},
}


@st.cache_resource
def get_calculator():
    return OctaneCalculator()


def main():
    st.title("⛽ Расчет октанового числа по хроматографии")
    st.caption("PIONA-анализ • Автоидентификация по LRI • ГОСТ 32513")

    calc = get_calculator()

    # ================================================================
    # 📊 ГЛАВНОЕ ОКНО: ВВОД ДАННЫХ ХРОМАТОГРАММЫ
    # ================================================================
    st.markdown("---")
    st.markdown("### 📋 Ввод данных хроматограммы")

    # Кнопки управления
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("➕ Добавить строку", use_container_width=True):
            if "peaks_data" not in st.session_state:
                st.session_state.peaks_data = []
            st.session_state.peaks_data.append({"retention_time": 0.0, "content": 0.0, "name": ""})
            st.rerun()
    
    with col2:
        if st.button("🤖 Автоидентификация", use_container_width=True):
            if "peaks_data" in st.session_state:
                tolerance = st.session_state.get("lri_tolerance", 10.0)
                st.session_state.peaks_data = calc.auto_identify_all_peaks(
                    st.session_state.peaks_data, tolerance
                )
                st.success(f"✅ Автоматическая идентификация завершена (допуск ΔLRI ≤ {tolerance})")
                st.rerun()
    
    with col3:
        if st.button("🗑️ Очистить все", use_container_width=True):
            st.session_state.peaks_data = []
            st.rerun()

    # Инициализация данных
    if "peaks_data" not in st.session_state:
        st.session_state.peaks_data = [
            {"retention_time": 3.45, "content": 1.50, "name": "н-Пентан"},
            {"retention_time": 3.28, "content": 4.20, "name": "Изопентан"},
            {"retention_time": 5.23, "content": 3.20, "name": "н-Гексан"},
            {"retention_time": 6.15, "content": 0.80, "name": "Бензол"},
            {"retention_time": 8.12, "content": 2.10, "name": "н-Гептан"},
            {"retention_time": 9.85, "content": 12.50, "name": "Толуол"},
            {"retention_time": 13.20, "content": 3.50, "name": "Этилбензол"},
            {"retention_time": 13.85, "content": 12.80, "name": "м-/п-Ксилол"},
            {"retention_time": 14.25, "content": 3.20, "name": "о-Ксилол"},
            {"retention_time": 12.45, "content": 0.90, "name": "н-Октан"},
            {"retention_time": 11.20, "content": 15.50, "name": "Изооктан"},
            {"retention_time": 10.05, "content": 8.00, "name": "МТБЭ"},
        ]

    # Таблица ввода данных
    st.info("💡 **Инструкция:** Введите время удерживания (tR) и концентрацию. "
            "Название компонента можно указать вручную или использовать кнопку «Автоидентификация».")

    # Допуск для автоидентификации
    col_tol1, col_tol2 = st.columns([1, 3])
    with col_tol1:
        tolerance = st.number_input("Допуск ΔLRI", min_value=1.0, max_value=20.0, 
                                    value=10.0, step=0.5, key="lri_tolerance")

    # Редактируемая таблица
    peaks_df = pd.DataFrame(st.session_state.peaks_data)
    
    edited_df = st.data_editor(
        peaks_df,
        column_config={
            "retention_time": st.column_config.NumberColumn(
                "tR, мин", min_value=0.0, max_value=100.0, step=0.01, format="%.2f"
            ),
            "content": st.column_config.NumberColumn(
                "Концентрация, %", min_value=0.0, max_value=100.0, step=0.01, format="%.2f"
            ),
            "name": st.column_config.TextColumn(
                "Название компонента",
                help="Оставьте пустым для автоидентификации",
            ),
        },
        hide_index=True,
        use_container_width=True,
        num_rows="dynamic",
        key="peaks_editor"
    )

    # Сохранение изменений
    st.session_state.peaks_data = edited_df.to_dict("records")

    # Загрузка из CSV
    st.markdown("---")
    col_csv1, col_csv2 = st.columns(2)
    with col_csv1:
        uploaded_csv = st.file_uploader("📄 Загрузить из CSV", type=["csv"])
        if uploaded_csv:
            try:
                csv_df = pd.read_csv(uploaded_csv)
                if "retention_time" in csv_df.columns and "content" in csv_df.columns:
                    name_col = "name" if "name" in csv_df.columns else None
                    st.session_state.peaks_data = []
                    for _, row in csv_df.iterrows():
                        peak = {
                            "retention_time": float(row["retention_time"]),
                            "content": float(row["content"]),
                            "name": str(row.get("name", "")) if name_col else ""
                        }
                        st.session_state.peaks_data.append(peak)
                    st.success(f"✅ Загружено {len(st.session_state.peaks_data)} пиков")
                    st.rerun()
                else:
                    st.error("CSV должен содержать столбцы: `retention_time`, `content`")
            except Exception as e:
                st.error(f"Ошибка чтения CSV: {e}")

    with col_csv2:
        st.download_button(
            "💾 Скачать шаблон CSV",
            data="retention_time,content,name\n3.45,1.50,н-Пентан\n5.23,3.20,н-Гексан\n8.12,2.10,н-Гептан\n",
            file_name="chromatogram_template.csv",
            mime="text/csv",
        )

    # ================================================================
    # 🧮 РАСЧЕТ
    # ================================================================
    st.markdown("---")
    
    # Фильтрация пустых строк
    valid_peaks = [p for p in st.session_state.peaks_data 
                   if p.get("retention_time", 0) > 0 and p.get("content", 0) > 0 and p.get("name", "").strip()]
    
    if not valid_peaks:
        st.warning("⚠️ Нет данных для расчета. Заполните таблицу выше.")
        return

    result = calc.calculate(valid_peaks, normalize=True)

    if "error" in result:
        st.error(result["error"])
        return

    # ================================================================
    # 📈 РЕЗУЛЬТАТЫ
    # ================================================================
    st.markdown("### 📊 Результаты расчета")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🔬 RON (Иссл.)", result["ron"])
    c2.metric("⚙️ MON (Мотор.)", result["mon"])
    c3.metric("📊 AKI (R+M)/2", result["aki"])
    c4.metric("📈 Чувствительность", result["sensitivity"])

    # Соответствие ГОСТ
    st.markdown("---")
    st.markdown("### 📋 Соответствие ГОСТ 32513-2013")
    comparison_data = []
    for mark, std in GOST_STANDARDS.items():
        ron_ok = "✅" if result["ron"] >= std["RON_min"] else "❌"
        mon_ok = "✅" if result["mon"] >= std["MON_min"] else "❌"
        a_content = result["piona"]["A"]["content"]
        a_ok = "✅" if a_content <= std["A_max"] else "❌"
        comparison_data.append({
            "Марка": mark,
            f"RON ≥ {std['RON_min']}": f"{ron_ok} {result['ron']}",
            f"MON ≥ {std['MON_min']}": f"{mon_ok} {result['mon']}",
            f"Ароматика ≤ {std['A_max']}%": f"{a_ok} {a_content}",
        })
    st.dataframe(pd.DataFrame(comparison_data), use_container_width=True, hide_index=True)

    # PIONA-анализ
    st.markdown("---")
    st.markdown("### 📊 Групповой состав (PIONA)")
    tab1, tab2 = st.tabs(["Круговая диаграмма", "Таблица"])

    piona_df = pd.DataFrame([
        {"Класс": CLASS_NAMES[k], "Содержание, %": v["content"], "Код": k}
        for k, v in result["piona"].items() if v["content"] > 0
    ])

    with tab1:
        fig_pie = px.pie(
            piona_df, values="Содержание, %", names="Класс",
            color="Код", color_discrete_map=CLASS_COLORS, hole=0.4,
        )
        fig_pie.update_traces(textposition="inside", textinfo="percent+label")
        fig_pie.update_layout(margin=dict(l=20, r=20, t=20, b=20), height=400)
        st.plotly_chart(fig_pie, use_container_width=True)

    with tab2:
        st.dataframe(
            pd.DataFrame([
                {"Класс": CLASS_NAMES[k], "Содержание, %": v["content"], 
                 "Ср. RON": v["avg_ron"], "Ср. MON": v["avg_mon"]}
                for k, v in result["piona"].items() if v["content"] > 0
            ]),
            use_container_width=True, hide_index=True,
        )

    # Детализация по компонентам
    st.markdown("---")
    st.markdown("### 🔬 Детализация по компонентам")
    
    groups_df = pd.DataFrame(result["groups"])
    groups_df["Класс"] = groups_df["class"].map(CLASS_NAMES)
    st.dataframe(
        groups_df[["name", "Класс", "content", "ron", "mon", "ron_contrib", "mon_contrib"]]
        .rename(columns={
            "name": "Компонент", "content": "Содерж., %",
            "ron": "RON", "mon": "MON",
            "ron_contrib": "Вклад RON", "mon_contrib": "Вклад MON",
        })
        .sort_values(["Класс", "content"], ascending=[True, False])
        .round(2),
        use_container_width=True, hide_index=True,
    )

    # Неидентифицированные компоненты
    if result["unknown"]:
        st.warning("⚠️ Неидентифицированные компоненты (не учтены в расчете):")
        for u in result["unknown"]:
            st.write(f"• {u}")

    # Экспорт результатов
    st.markdown("---")
    st.markdown("### 💾 Экспорт результатов")
    export_df = pd.DataFrame([
        {"Параметр": "RON (Исследовательское)", "Значение": result["ron"]},
        {"Параметр": "MON (Моторное)", "Значение": result["mon"]},
        {"Параметр": "AKI (R+M)/2", "Значение": result["aki"]},
        {"Параметр": "Чувствительность", "Значение": result["sensitivity"]},
    ])
    csv = export_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button("⬇️ Скачать отчет (CSV)", csv, "octane_report.csv", "text/csv")

    st.markdown("---")
    st.caption("© 2026 • PIONA + LRI • ASTM D6730 / ГОСТ 32513")


if __name__ == "__main__":
    main()
