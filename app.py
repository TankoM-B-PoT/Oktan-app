"""
Веб-приложение для расчета октанового числа бензина по данным хроматографии.
Streamlit + Plotly + Pandas.
Полная база компонентов + автоидентификация по LRI.
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
    "P": "Парафины (н-алканы)", "I": "Изопарафины", "O": "Олефины",
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
    st.caption("PIONA-анализ • Автоидентификация по LRI (HP-5/DB-5) • ГОСТ 32513")

    calc = get_calculator()

    # ================================================================
    # 📋 ВВОД ДАННЫХ ХРОМАТОГРАММЫ
    # ================================================================
    st.markdown("---")
    st.markdown("### 📋 Ввод данных хроматограммы")

    # Кнопки управления
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("➕ Добавить строку", use_container_width=True):
            if "peaks_data" not in st.session_state:
                st.session_state.peaks_data = []
            st.session_state.peaks_data.append({
                "retention_time": 0.0,
                "content": 0.0,
                "name": ""
            })
            st.rerun()
    with col2:
        overwrite = st.checkbox("🔄 Перезаписать имена", value=False,
                                help="Если включено — автоидентификация заменит даже заполненные имена")
    with col3:
        if st.button("🤖 Автоидентификация", use_container_width=True, type="primary"):
            if "peaks_data" in st.session_state and st.session_state.peaks_data:
                tolerance = st.session_state.get("lri_tolerance", 10.0)
                updated, diagnostics = calc.identify_all_peaks(
                    st.session_state.peaks_data, tolerance, overwrite
                )
                st.session_state.peaks_data = updated
                st.session_state.last_diagnostics = diagnostics
                st.success(f"✅ Идентификация завершена (допуск ΔLRI ≤ {tolerance})")
                st.rerun()
            else:
                st.warning("⚠️ Таблица пуста")
    with col4:
        if st.button("🗑️ Очистить", use_container_width=True):
            st.session_state.peaks_data = []
            if "last_diagnostics" in st.session_state:
                del st.session_state.last_diagnostics
            st.rerun()

    # Инициализация демо-данных
    if "peaks_data" not in st.session_state:
        st.session_state.peaks_data = [
            {"retention_time": 3.45, "content": 1.50, "name": "н-пентан"},
            {"retention_time": 5.23, "content": 3.20, "name": "н-гексан"},
            {"retention_time": 8.12, "content": 2.10, "name": "н-гептан"},
            {"retention_time": 12.45, "content": 0.90, "name": "н-октан"},
            {"retention_time": 9.85, "content": 12.50, "name": ""},
            {"retention_time": 13.85, "content": 12.80, "name": ""},
        ]

    # Допуск для автоидентификации
    tolerance = st.number_input("Допуск ΔLRI (ед.)", min_value=1.0, max_value=30.0,
                                value=10.0, step=0.5, key="lri_tolerance")

    # Инструкция
    st.info("💡 **Как пользоваться:**\n"
            "1. Введите **tR** (время удерживания, мин) и **Концентрацию** (%)\n"
            "2. Оставьте **Название пустым** — программа сама определит компонент по LRI\n"
            "3. Или введите название вручную\n"
            "4. Нажмите **🤖 Автоидентификация**\n"
            "5. Для корректной работы нужно ≥2 н-алканов (н-пентан, н-гексан, н-гептан, н-октан)")

    # Редактируемая таблица
    peaks_df = pd.DataFrame(st.session_state.peaks_data)
    edited_df = st.data_editor(
        peaks_df,
        column_config={
            "retention_time": st.column_config.NumberColumn(
                "tR, мин", min_value=0.0, max_value=100.0, step=0.01, format="%.2f"),
            "content": st.column_config.NumberColumn(
                "Концентрация, %", min_value=0.0, max_value=100.0, step=0.01, format="%.2f"),
            "name": st.column_config.TextColumn(
                "Название (оставьте пустым для автоопределения)"),
        },
        hide_index=True,
        use_container_width=True,
        num_rows="dynamic",
        key="peaks_editor"
    )
    st.session_state.peaks_data = edited_df.to_dict("records")

    # Загрузка/выгрузка CSV
    st.markdown("---")
    col_csv1, col_csv2 = st.columns(2)
    with col_csv1:
        uploaded_csv = st.file_uploader("📄 Загрузить из CSV", type=["csv"])
        if uploaded_csv:
            try:
                csv_df = pd.read_csv(uploaded_csv)
                if "retention_time" in csv_df.columns and "content" in csv_df.columns:
                    st.session_state.peaks_data = []
                    for _, row in csv_df.iterrows():
                        peak = {
                            "retention_time": float(row["retention_time"]),
                            "content": float(row["content"]),
                            "name": str(row.get("name", "")) if "name" in csv_df.columns else ""
                        }
                        st.session_state.peaks_data.append(peak)
                    st.success(f"✅ Загружено {len(st.session_state.peaks_data)} пиков")
                    st.rerun()
                else:
                    st.error("CSV должен содержать столбцы: `retention_time`, `content`")
            except Exception as e:
                st.error(f"Ошибка: {e}")
    with col_csv2:
        st.download_button(
            "💾 Шаблон CSV",
            data="retention_time,content,name\n3.45,1.50,н-пентан\n5.23,3.20,н-гексан\n8.12,2.10,н-гептан\n12.45,0.90,н-октан\n9.85,12.50,\n13.85,12.80,\n",
            file_name="chromatogram_template.csv",
            mime="text/csv",
        )

    # ================================================================
    # 🔍 ДИАГНОСТИКА АВТОИДЕНТИФИКАЦИИ
    # ================================================================
    if "last_diagnostics" in st.session_state and st.session_state.last_diagnostics:
        st.markdown("---")
        st.markdown("### 🔍 Результаты автоидентификации")

        diag_df = pd.DataFrame(st.session_state.last_diagnostics)
        if not diag_df.empty:
            display_cols = ["retention_time", "lri", "nearest", "deviation", "reason"]
            available_cols = [c for c in display_cols if c in diag_df.columns]
            diag_display = diag_df[available_cols].copy()
            diag_display.columns = ["tR, мин", "LRI расч.", "Ближайший компонент", "ΔLRI", "Статус"]
            st.dataframe(diag_display, use_container_width=True, hide_index=True)

            failed = diag_df[diag_df['name'].isna()]
            if not failed.empty:
                st.warning(f"⚠️ Не идентифицировано пиков: {len(failed)}")
                for _, row in failed.iterrows():
                    st.write(f"• tR={row['retention_time']:.2f} мин — {row['reason']}")

    # ================================================================
    # 🧮 РАСЧЕТ ОКТАНОВОГО ЧИСЛА
    # ================================================================
    st.markdown("---")

    valid_peaks = [p for p in st.session_state.peaks_data
                   if p.get("retention_time", 0) > 0 and p.get("content", 0) > 0 and p.get("name", "").strip()]

    if not valid_peaks:
        st.warning("⚠️ Нет данных для расчета. Заполните таблицу выше.")
        return

    result = calc.calculate(valid_peaks, normalize=True)

    if "error" in result:
        st.error(result["error"])
        return

    # Ключевые показатели
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
        if not piona_df.empty:
            fig_pie = px.pie(
                piona_df, values="Содержание, %", names="Класс",
                color="Код", color_discrete_map=CLASS_COLORS, hole=0.4,
            )
            fig_pie.update_traces(textposition="inside", textinfo="percent+label")
            fig_pie.update_layout(margin=dict(l=20, r=20, t=20, b=20), height=400)
            st.plotly_chart(fig_pie, use_container_width=True)

    with tab2:
        piona_table = pd.DataFrame([
            {"Класс": CLASS_NAMES[k], "Содержание, %": v["content"],
             "Ср. RON": v["avg_ron"], "Ср. MON": v["avg_mon"]}
            for k, v in result["piona"].items() if v["content"] > 0
        ])
        st.dataframe(piona_table, use_container_width=True, hide_index=True)

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
        {"Параметр": "Чувствительность (RON-MON)", "Значение": result["sensitivity"]},
        {"Параметр": "Сумма концентраций, %", "Значение": result["total_content"]},
    ])
    csv = export_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button("⬇️ Скачать отчет (CSV)", csv, "octane_report.csv", "text/csv")

    # Справка
    with st.expander("📚 Справка по методике"):
        st.markdown("""
        **Методика расчета:**
        - Линейная модель смешения октановых чисел
        - PIONA-анализ по ASTM D6730 / ГОСТ Р 52709
        - LRI (линейный индекс удерживания) по Ван ден Дулу и Кратцу для режима программирования температуры
        
        **Колонка:** HP-5 / DB-5 (5% фенил-метилполисилоксан)
        
        **Порядок элюирования C8-ароматики:**
        1. Этилбензол (LRI ~850)
        2. п-Ксилол + м-Ксилол (co-elution, LRI ~868)
        3. о-Ксилол (LRI ~885)
        
        **Нормативы:** ГОСТ 32513-2013 "Топлива моторные. Бензин неэтилированный"
        """)

    st.markdown("---")
    st.caption("© 2026 • PIONA + LRI • ASTM D6730 / ГОСТ 32513 / ГОСТ Р 52709")


if __name__ == "__main__":
    main()
