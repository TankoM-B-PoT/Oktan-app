"""
Веб-приложение для расчета октанового числа бензина по данным хроматографии.
Streamlit + Plotly + Pandas
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from calculator import OctaneCalculator

st.set_page_config(
    page_title="Расчет октанового числа",
    page_icon="⛽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Цвета классов PIONA
CLASS_COLORS = {
    "P": "#2E86AB", "I": "#A23B72", "O": "#F18F01",
    "N": "#C73E1D", "A": "#3B1F2B", "OXY": "#44BBA4",
}
CLASS_NAMES = {
    "P": "Парафины", "I": "Изопарафины", "O": "Олефины",
    "N": "Нафтены", "A": "Ароматика", "OXY": "Кислородсодержащие",
}

# Нормативы ГОСТ 32513-2013
GOST_STANDARDS = {
    "АИ-92":  {"RON_min": 92.0,  "MON_min": 82.0, "A_max": 25, "O_max": 18},
    "АИ-95":  {"RON_min": 95.0,  "MON_min": 85.0, "A_max": 30, "O_max": 15},
    "АИ-98":  {"RON_min": 98.0,  "MON_min": 88.0, "A_max": 35, "O_max": 15},
    "АИ-100": {"RON_min": 100.0, "MON_min": 90.0, "A_max": 35, "O_max": 15},
}

# Опорные пики
ANCHOR_PEAKS = [
    "н-Пентан", "Изопентан", "н-Гексан", "Бензол", "н-Гептан", "Толуол",
    "н-Октан", "Изооктан", "Этилбензол", "п-Ксилол", "м-Ксилол", "м-/п-Ксилол", "о-Ксилол",
    "н-Нонан", "н-Декан"
]

# Порядок элюирования C8-ароматики
C8_AROMATICS_ORDER = ["Этилбензол", "м-/п-Ксилол", "п-Ксилол", "м-Ксилол", "о-Ксилол"]


@st.cache_resource
def get_calculator():
    return OctaneCalculator()


def main():
    st.title("⛽ Расчет октанового числа по хроматографии")
    st.caption("PIONA-анализ • Изомеры C8–C10 • LRI (Ван ден Дул и Кратц) • ГОСТ 32513")

    calc = get_calculator()

    # ================================================================
    # 🎛️ БОКОВАЯ ПАНЕЛЬ
    # ================================================================
    with st.sidebar:
        # ---------- КАЛИБРОВКА LRI ----------
        st.header("⚙️ Калибровка LRI")
        lri_source = st.radio(
            "Источник табличных LRI:",
            ["📚 Встроенная БД", "📄 Загрузить CSV", "✏️ Ручной ввод"],
            help="Позволяет калибровать программу под вашу колонку и метод"
        )

        lri_template = ("group,table_lri,description\n"
                        "н-Пентан,500.0,н-пентан\n"
                        "н-Гексан,600.0,н-гексан\n"
                        "н-Гептан,700.0,н-гептан\n"
                        "Толуол,765.0,толуол\n"
                        "н-Октан,800.0,н-октан\n"
                        "Этилбензол,852.0,этилбензол\n"
                        "м-/п-Ксилол,872.0,м- + п-ксилол\n"
                        "о-Ксилол,888.0,о-ксилол\n")

        st.download_button("⬇️ Шаблон CSV для LRI", data=lri_template,
                           file_name="lri_template.csv", mime="text/csv")
        st.download_button("💾 Экспорт текущей таблицы LRI",
                           data=calc.export_lri_table(),
                           file_name="current_lri_table.csv", mime="text/csv")

        if lri_source == "📄 Загрузить CSV":
            uploaded_lri = st.file_uploader("CSV с LRI", type=["csv"], key="lri_upload")
            if uploaded_lri:
                try:
                    lri_df = pd.read_csv(uploaded_lri)
                    if "group" in lri_df.columns and "table_lri" in lri_df.columns:
                        load_result = calc.load_custom_lri_table(
                            lri_df[["group", "table_lri"]].to_dict("records")
                        )
                        if load_result["updated"]:
                            st.success(f"✅ Обновлено {len(load_result['updated'])} значений")
                        if load_result["not_found"]:
                            st.warning(f"⚠️ Не найдены в БД: {', '.join(load_result['not_found'])}")
                        if load_result["errors"]:
                            st.error(f"❌ Ошибки: {', '.join(load_result['errors'])}")
                    else:
                        st.error("CSV должен содержать столбцы: `group`, `table_lri`")
                except Exception as e:
                    st.error(f"Ошибка чтения CSV: {e}")

        elif lri_source == "✏️ Ручной ввод":
            current_table = calc.get_lri_table()
            edited_df = st.data_editor(
                pd.DataFrame(current_table)[["group", "description", "table_lri"]],
                column_config={
                    "group": st.column_config.TextColumn("Группа", disabled=True),
                    "description": st.column_config.TextColumn("Описание", disabled=True),
                    "table_lri": st.column_config.NumberColumn(
                        "Табличный LRI", min_value=0.0, max_value=2000.0,
                        step=1.0, format="%.1f"),
                },
                hide_index=True, use_container_width=True, num_rows="fixed",
                key="lri_editor"
            )
            if st.button("💾 Применить изменения", type="primary"):
                updated_count = 0
                for _, row in edited_df.iterrows():
                    old_lri = next((item["table_lri"] for item in current_table
                                    if item["group"] == row["group"]), None)
                    if old_lri is not None and abs(row["table_lri"] - old_lri) > 0.01:
                        calc.update_table_lri(row["group"], row["table_lri"])
                        updated_count += 1
                if updated_count > 0:
                    st.success(f"✅ Обновлено {updated_count} значений LRI")
                    st.rerun()
                else:
                    st.info("ℹ️ Изменений не обнаружено")
        else:
            with st.expander("📋 Просмотр встроенной таблицы LRI"):
                st.dataframe(
                    pd.DataFrame(calc.get_lri_table())[["group", "class", "description", "table_lri"]]
                    .rename(columns={"group": "Группа", "class": "Класс",
                                     "description": "Описание", "table_lri": "Табличный LRI"}),
                    use_container_width=True, hide_index=True,
                )

        st.markdown("---")

        # ---------- ИСТОЧНИК ДАННЫХ ХРОМАТОГРАММЫ ----------
        st.header("📥 Данные хроматограммы")
        data_source = st.radio(
            "Способ ввода:",
            ["📄 Загрузить CSV", "✏️ Ручной ввод", "🎯 Демо-пример"],
        )

        csv_template = ("group,content,retention_time\n"
                        "н-Пентан,1.50,3.45\n"
                        "Изопентан,4.20,3.28\n"
                        "н-Гексан,3.20,5.23\n"
                        "Бензол,0.80,6.15\n"
                        "н-Гептан,2.10,8.12\n"
                        "Толуол,12.50,9.85\n"
                        "Этилбензол,3.50,13.20\n"
                        "м-/п-Ксилол,12.80,13.85\n"
                        "о-Ксилол,3.20,14.25\n"
                        "н-Октан,0.90,12.45\n"
                        "Изооктан,15.50,11.20\n"
                        "МТБЭ,8.00,10.05\n")
        st.download_button("⬇️ Шаблон CSV для хроматограммы", data=csv_template,
                           file_name="chromatogram_template.csv", mime="text/csv")

    # ================================================================
    # 📊 ПОЛУЧЕНИЕ ДАННЫХ
    # ================================================================
    df = None
    if data_source == "📄 Загрузить CSV":
        uploaded = st.file_uploader("Выберите CSV-файл хроматограммы", type=["csv"])
        if uploaded:
            df = pd.read_csv(uploaded)
            if "group" not in df.columns or "content" not in df.columns:
                st.error("CSV должен содержать столбцы: `group`, `content` (и опционально `retention_time`)")
                df = None

    elif data_source == "✏️ Ручной ввод":
        st.info("Введите данные. Пустые строки игнорируются.")
        groups_list = list(calc.db.keys())
        manual_data = []
        for g in groups_list:
            col1, col2, col3 = st.columns([3, 2, 2])
            with col1:
                val = st.number_input(g, min_value=0.0, max_value=100.0, value=0.0,
                                      step=0.1, key=f"m_{g}")
            with col2:
                rt = st.number_input("tR, мин", min_value=0.0, max_value=100.0, value=0.0,
                                     step=0.01, key=f"rt_{g}", label_visibility="collapsed")
            if val > 0:
                row = {"group": g, "content": val}
                if rt > 0:
                    row["retention_time"] = rt
                manual_data.append(row)
        df = pd.DataFrame(manual_data) if manual_data else None

    else:  # Демо
        demo = [
            ("н-Пентан", 1.50, 3.45), ("Изопентан", 4.20, 3.28),
            ("н-Гексан", 3.20, 5.23), ("Бензол", 0.80, 6.15),
            ("н-Гептан", 2.10, 8.12), ("Толуол", 12.50, 9.85),
            ("Этилбензол", 3.50, 13.20), ("м-/п-Ксилол", 12.80, 13.85),
            ("о-Ксилол", 3.20, 14.25), ("н-Октан", 0.90, 12.45),
            ("Изооктан", 15.50, 11.20), ("МТБЭ", 8.00, 10.05),
            ("C6-ол", 2.30, 5.80), ("N-C6", 4.50, 6.50),
        ]
        df = pd.DataFrame(demo, columns=["group", "content", "retention_time"])

    # ================================================================
    # 🧮 РАСЧЕТ
    # ================================================================
    if df is None or df.empty:
        st.info("👈 Загрузите данные или выберите демо-пример в боковой панели.")
        return

    data = df.to_dict("records")
    result = calc.calculate(data, normalize=True)

    if "error" in result:
        st.error(result["error"])
        return

    # ================================================================
    # 📈 КЛЮЧЕВЫЕ ПОКАЗАТЕЛИ
    # ================================================================
    st.markdown("---")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🔬 RON (Иссл.)", result["ron"])
    c2.metric("⚙️ MON (Мотор.)", result["mon"])
    c3.metric("📊 AKI (R+M)/2", result["aki"])
    c4.metric("📈 Чувствительность", result["sensitivity"])

    # ================================================================
    # 🎯 ОПОРНЫЕ ПИКИ
    # ================================================================
    st.markdown("---")
    st.markdown("### 🎯 Статус базовых опорных пиков")

    df_records = df.to_dict("records")
    found_anchors = []
    for g in result["groups"]:
        if g["group"] in ANCHOR_PEAKS:
            rt = next((item.get("retention_time") for item in df_records
                       if str(item.get("group", "")).strip() == g["group"]), None)
            status = "✅ Найден"
            if g["group"] == "м-/п-Ксилол":
                status = "✅ Объединенный пик (co-elution)"
            elif g["group"] in ["п-Ксилол", "м-Ксилол"]:
                status = "⚠️ Разделенный пик"
            found_anchors.append({
                "Пик": g["group"],
                "Содерж., %": g["content"],
                "RON": g["ron"], "MON": g["mon"],
                "tR, мин": f"{rt:.2f}" if rt else "Н/Д",
                "Статус": status,
            })

    if found_anchors:
        anchors_df = pd.DataFrame(found_anchors)
        st.dataframe(anchors_df, use_container_width=True, hide_index=True)

        # Проверка порядка элюирования C8-ароматики
        rt_list = [(row["Пик"], float(row["tR, мин"]))
                   for _, row in anchors_df.iterrows()
                   if row["tR, мин"] != "Н/Д" and row["Пик"] in C8_AROMATICS_ORDER]
        rt_list.sort(key=lambda x: x[1])
        c8_actual = [name for name, _ in rt_list]

        if c8_actual:
            st.markdown("**Порядок элюирования C8-ароматики:**")
            st.info(" → ".join([f"`{n}` ({t:.2f} мин)" for n, t in rt_list]))

            # Проверка: этилбензол должен быть первым, о-ксилол — последним
            if c8_actual[0] == "Этилбензол" and c8_actual[-1] == "о-Ксилол":
                st.success("✅ Порядок элюирования C8-ароматики корректен!")
            else:
                st.warning("⚠️ Проверьте порядок элюирования C8-ароматики. "
                           "Ожидается: Этилбензол → (м-/п-Ксилол) → о-Ксилол")
    else:
        st.warning("⚠️ Опорные пики не найдены. Проверьте названия в CSV.")

    # ================================================================
    # 🔍 ПРОВЕРКА РАЗМЕТКИ ПО LRI
    # ================================================================
    st.markdown("---")
    st.markdown("### 🔍 Проверка разметки хроматограммы (LRI)")
    st.caption("Линейный индекс удерживания (Ван ден Дул и Кратц) для программируемой температуры")

    has_rt = "retention_time" in df.columns and df["retention_time"].notna().any()

    if not has_rt:
        st.warning("⚠️ В данных отсутствует столбец `retention_time`. "
                   "Добавьте его для проверки идентификации пиков.")
    else:
        source_label = {"📚 Встроенная БД": "📚 Встроенная база",
                        "📄 Загрузить CSV": "📄 Пользовательский CSV",
                        "✏️ Ручной ввод": "✏️ Отредактированные значения"}
        st.info(f"Используются табличные LRI: {source_label.get(lri_source, lri_source)}")

        tolerance = st.number_input("Допуск ΔLRI (ед.)", min_value=1.0, max_value=20.0,
                                    value=5.0, step=0.5)

        check_result = calc.check_peak_identification(data, tolerance=tolerance)

        if check_result["warnings"]:
            for w in check_result["warnings"]:
                st.warning(w)

        if check_result["peaks"]:
            stats = check_result["statistics"]
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Всего пиков", stats["total_peaks"])
            col2.metric("✅ Корректно", stats["correct"],
                        delta=f"{stats['correct']/stats['total_peaks']*100:.0f}%")
            col3.metric("❌ Ошибки", stats["incorrect"])
            col4.metric("Макс. |ΔLRI|", stats["max_deviation"])

            check_df = pd.DataFrame(check_result["peaks"])
            st.dataframe(
                check_df[["group", "retention_time", "calculated_lri",
                          "table_lri", "deviation", "status", "content"]]
                .rename(columns={
                    "group": "Группа", "retention_time": "tR, мин",
                    "calculated_lri": "LRI расч.", "table_lri": "LRI табл.",
                    "deviation": "ΔLRI", "status": "Статус", "content": "Содерж., %"
                })
                .sort_values("deviation", key=abs, ascending=False),
                use_container_width=True, hide_index=True,
            )

            fig_dev = px.bar(
                check_df, x="group", y="deviation",
                color="status", color_discrete_map={"✅": "#2E86AB", "❌": "#C73E1D"},
                labels={"deviation": "ΔLRI", "group": "Группа"},
            )
            fig_dev.add_hline(y=0, line_dash="dash", line_color="gray")
            fig_dev.add_hline(y=tolerance, line_dash="dot", line_color="orange",
                              annotation_text=f"+{tolerance}")
            fig_dev.add_hline(y=-tolerance, line_dash="dot", line_color="orange",
                              annotation_text=f"-{tolerance}")
            fig_dev.update_layout(height=400, xaxis_tickangle=-45)
            st.plotly_chart(fig_dev, use_container_width=True)

            if stats["incorrect"] > 0:
                with st.expander("💡 Рекомендации по калибровке"):
                    st.markdown("""
                    **Систематическое смещение** (все пики в одну сторону):
                    - Проверьте температуру печи и скорость потока газа-носителя
                    - Проверьте герметичность системы

                    **Случайные отклонения**:
                    - Проверьте интеграцию пиков
                    - Возможна ко-элюция (наложение пиков)

                    **Калибровка под вашу колонку**:
                    - Загрузите CSV с табличными LRI в разделе "Калибровка LRI"
                    """)

    # ================================================================
    # 📋 СРАВНЕНИЕ С ГОСТ
    # ================================================================
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

    # ================================================================
    # 📊 PIONA-АНАЛИЗ
    # ================================================================
    st.markdown("---")
    st.markdown("### 📊 Групповой углеводородный состав (PIONA)")
    tab1, tab2 = st.tabs(["Круговая диаграмма", "Столбчатая диаграмма"])

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
        fig_bar = px.bar(
            piona_df, x="Класс", y="Содержание, %",
            color="Код", color_discrete_map=CLASS_COLORS,
            text="Содержание, %",
        )
        fig_bar.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig_bar, use_container_width=True)

    # ================================================================
    # 🔬 ДЕТАЛИЗАЦИЯ ПО ГРУППАМ
    # ================================================================
    st.markdown("---")
    st.markdown("### 🔬 Детализация по компонентам")

    selected_classes = st.multiselect(
        "Фильтр по классам:",
        ["P", "I", "O", "N", "A", "OXY"],
        default=["P", "I", "O", "N", "A", "OXY"],
        format_func=lambda x: CLASS_NAMES[x],
    )

    filtered = [g for g in result["groups"] if g["class"] in selected_classes]
    if filtered:
        groups_df = pd.DataFrame(filtered)
        groups_df["Класс"] = groups_df["class"].map(CLASS_NAMES)
        st.dataframe(
            groups_df[["group", "Класс", "content", "ron", "mon", "ron_contrib", "mon_contrib"]]
            .rename(columns={
                "group": "Группа", "content": "Содерж., %",
                "ron": "RON", "mon": "MON",
                "ron_contrib": "Вклад RON", "mon_contrib": "Вклад MON",
            })
            .sort_values(["Класс", "content"], ascending=[True, False])
            .round(2),
            use_container_width=True, hide_index=True,
        )

        # График распределения изомеров C8-C10
        iso_groups = [g for g in filtered if g["group"].endswith(("C7", "C8", "C9", "MeC5",
                                                                   "MeC6", "MeC7", "MeC8", "MeC9",
                                                                   "diMeC4", "diMeC6", "diMeC7",
                                                                   "diMeC8", "triMeC5", "triMeC6",
                                                                   "triMeC7", "tetraMeC4"))
                      or "Et-" in g["group"]]
        if iso_groups:
            st.markdown("**Распределение изомеров C8–C10:**")
            iso_df = pd.DataFrame(iso_groups)
            fig_iso = px.bar(
                iso_df, x="group", y="content", color="class",
                color_discrete_map=CLASS_COLORS,
                labels={"content": "Содержание, %", "group": "Изомер"},
            )
            fig_iso.update_layout(height=400, xaxis_tickangle=-45, showlegend=False)
            st.plotly_chart(fig_iso, use_container_width=True)

    # ================================================================
    # ⚠️ ПРЕДУПРЕЖДЕНИЯ
    # ================================================================
    if result["unknown"]:
        st.warning("⚠️ Неидентифицированные компоненты (не учтены в расчете):")
        for u in result["unknown"]:
            st.write(f"• {u}")

    # ================================================================
    # 💾 ЭКСПОРТ
    # ================================================================
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

    # ================================================================
    # 📚 СПРАВКА
    # ================================================================
    with st.expander("📚 Справка по методике"):
        st.markdown("""
        **Методика расчета:**
        - Линейная модель смешения октановых чисел
        - PIONA-анализ по ASTM D6730 / ГОСТ Р 52709
        - LRI (линейный индекс удерживания) по Ван ден Дулу и Кратцу для режима программирования температуры

        **Порядок элюирования C8-ароматики (неполярная колонка HP-5/DB-5):**
        1. Этилбензол (LRI ~850)
        2. п-Ксилол + м-Ксилол (co-elution, LRI ~868)
        3. о-Ксилол (LRI ~885)

        **Нормативы:** ГОСТ 32513-2013 "Топлива моторные. Бензин неэтилированный"
        """)

    st.markdown("---")
    st.caption("© 2026 • PIONA + LRI • ASTM D6730 / ГОСТ 32513 / ГОСТ Р 52709")


if __name__ == "__main__":
    main()
