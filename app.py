"""
Веб-приложение для расчета октанового числа бензина по данным хроматографии.
Streamlit + Plotly + Pandas.

Исправления относительно первой версии:
  * Устранён бесконечный цикл при загрузке CSV (tracking по file_id).
  * Пустая таблица корректно получает колонки для редактирования.
  * Защита от None в retention_time / content / name (используется `or 0`).
  * Flash-сообщения через session_state (видны после st.rerun).
  * Версионирование key data_editor при программном изменении данных.
  * Безопасное переименование колонок диагностики.
  * CSV: NaN-имена не превращаются в строку 'nan'.
  * Показ якорей и статусов идентификации.
  * number_input допуска вынесен выше кнопки автоидентификации.
  * Убран устаревший use_container_width в пользу width='stretch'.
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

DEMO_PEAKS = [
    {"retention_time": 3.45, "content": 1.50, "name": "н-пентан"},
    {"retention_time": 5.23, "content": 3.20, "name": "н-гексан"},
    {"retention_time": 8.12, "content": 2.10, "name": "н-гептан"},
    {"retention_time": 12.45, "content": 0.90, "name": "н-октан"},
    {"retention_time": 9.85, "content": 12.50, "name": ""},
    {"retention_time": 13.85, "content": 12.80, "name": ""},
]

PEAK_COLUMNS = ["retention_time", "content", "name"]


@st.cache_resource
def get_calculator() -> OctaneCalculator:
    return OctaneCalculator()


def flash(msg: str, kind: str = "success") -> None:
    """Кладём сообщение в session_state — оно покажется после rerun."""
    st.session_state.setdefault("_flashes", []).append((kind, msg))


def render_flashes() -> None:
    for kind, msg in st.session_state.pop("_flashes", []):
        getattr(st, kind)(msg)


def bump_editor_version() -> None:
    st.session_state.editor_version = st.session_state.get("editor_version", 0) + 1


def safe_float(value, default: float = 0.0) -> float:
    """Безопасное приведение к float с обработкой None/NaN/строк."""
    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
    except (TypeError, ValueError):
        pass
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_str(value) -> str:
    """Строка с превращением None/NaN в пустую."""
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    s = str(value).strip()
    return "" if s.lower() in ("nan", "none") else s


def main() -> None:
    st.title("⛽ Расчет октанового числа по хроматографии")
    st.caption("PIONA-анализ • Автоидентификация по LRI (HP-5/DB-5) • ГОСТ 32513")

    calc = get_calculator()
    render_flashes()

    # ── Инициализация состояния ─────────────────────────────────
    if "peaks_data" not in st.session_state:
        st.session_state.peaks_data = [dict(p) for p in DEMO_PEAKS]
    st.session_state.setdefault("editor_version", 0)

    # ============================================================
    # Ввод данных
    # ============================================================
    st.markdown("---")
    st.markdown("### 📋 Ввод данных хроматограммы")

    # Допуск — ВЫШЕ кнопок, чтобы значение было доступно при клике
    tolerance = st.number_input(
        "Допуск ΔLRI (ед.)",
        min_value=1.0, max_value=30.0, value=10.0, step=0.5,
        key="lri_tolerance",
    )

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("➕ Добавить строку", width="stretch"):
            st.session_state.peaks_data.append({
                "retention_time": 0.0, "content": 0.0, "name": "",
            })
            bump_editor_version()
            st.rerun()
    with col2:
        overwrite = st.checkbox(
            "🔄 Перезаписать имена", value=False,
            help="Авто-ID заменит даже заполненные имена, ЕСЛИ они не совпадают с LRI.",
        )
    with col3:
        if st.button("🤖 Автоидентификация", width="stretch", type="primary"):
            if not st.session_state.peaks_data:
                st.warning("⚠️ Таблица пуста")
            else:
                try:
                    updated, diagnostics = calc.identify_all_peaks(
                        st.session_state.peaks_data,
                        tolerance=st.session_state.get("lri_tolerance", 10.0),
                        overwrite=overwrite,
                    )
                    st.session_state.peaks_data = updated
                    st.session_state.last_diagnostics = diagnostics
                    bump_editor_version()
                    flash(
                        f"✅ Идентификация завершена (допуск ΔLRI ≤ "
                        f"{st.session_state.get('lri_tolerance', 10.0)})"
                    )
                    st.rerun()
                except Exception as e:
                    st.error(f"Ошибка идентификации: {e}")
    with col4:
        if st.button("🗑️ Очистить", width="stretch"):
            st.session_state.peaks_data = []
            st.session_state.pop("last_diagnostics", None)
            bump_editor_version()
            flash("🗑️ Таблица очищена")
            st.rerun()

    st.info(
        "💡 **Как пользоваться:**\n"
        "1. Введите **tR** (мин) и **Концентрацию** (%)\n"
        "2. Назовите хотя бы 2 н-алкана-якоря (н-пентан, н-гексан, н-гептан, н-октан)\n"
        "3. Остальные **Названия оставьте пустыми** — их определит программа\n"
        "4. Нажмите **🤖 Автоидентификация**\n\n"
        "ℹ️ Групповые компоненты (i-C8, N-C7 и т.п.) исключены из авто-ID — "
        "они для ручного ввода в случае неразделённых пиков."
    )

    # Редактор таблицы
    peaks_df = pd.DataFrame(
        st.session_state.peaks_data or [], columns=PEAK_COLUMNS
    )
    edited_df = st.data_editor(
        peaks_df,
        column_config={
            "retention_time": st.column_config.NumberColumn(
                "tR, мин", min_value=0.0, max_value=100.0,
                step=0.01, format="%.2f",
            ),
            "content": st.column_config.NumberColumn(
                "Концентрация, %", min_value=0.0, max_value=100.0,
                step=0.01, format="%.2f",
            ),
            "name": st.column_config.TextColumn(
                "Название (пусто = авто-ID)",
            ),
        },
        hide_index=True,
        width="stretch",
        num_rows="dynamic",
        key=f"peaks_editor_v{st.session_state.editor_version}",
    )
    st.session_state.peaks_data = edited_df.to_dict("records")

    # Показываем якоря
    anchors_str = calc.describe_anchors(st.session_state.peaks_data)
    st.caption(f"🔧 Якоря н-алканов: {anchors_str}")

    # ── CSV ────────────────────────────────────────────────────
    st.markdown("---")
    col_csv1, col_csv2 = st.columns(2)
    with col_csv1:
        uploaded_csv = st.file_uploader("📄 Загрузить из CSV", type=["csv"])
        if uploaded_csv is not None:
            file_id = f"{uploaded_csv.name}_{uploaded_csv.size}"
            if st.session_state.get("processed_csv") != file_id:
                try:
                    csv_df = pd.read_csv(uploaded_csv)
                    if "retention_time" not in csv_df.columns or "content" not in csv_df.columns:
                        st.error("CSV должен содержать столбцы: `retention_time`, `content`")
                    else:
                        new_peaks = []
                        for _, row in csv_df.iterrows():
                            new_peaks.append({
                                "retention_time": safe_float(row.get("retention_time")),
                                "content": safe_float(row.get("content")),
                                "name": safe_str(row.get("name", "")) if "name" in csv_df.columns else "",
                            })
                        st.session_state.peaks_data = new_peaks
                        st.session_state.processed_csv = file_id
                        bump_editor_version()
                        flash(f"✅ Загружено {len(new_peaks)} пиков")
                        st.rerun()
                except Exception as e:
                    st.error(f"Ошибка чтения CSV: {e}")
    with col_csv2:
        template = "retention_time,content,name\n3.45,1.50,н-пентан\n5.23,3.20,н-гексан\n8.12,2.10,н-гептан\n12.45,0.90,н-октан\n9.85,12.50,\n13.85,12.80,\n"
        st.download_button(
            "💾 Шаблон CSV",
            data=template.encode("utf-8-sig"),
            file_name="chromatogram_template.csv",
            mime="text/csv",
        )

    # ============================================================
    # Диагностика
    # ============================================================
    if st.session_state.get("last_diagnostics"):
        st.markdown("---")
        st.markdown("### 🔍 Результаты автоидентификации")

        diag_df = pd.DataFrame(st.session_state.last_diagnostics)
        if not diag_df.empty:
            display_cols = ["retention_time", "lri", "nearest", "deviation", "reason", "status"]
            available_cols = [c for c in display_cols if c in diag_df.columns]
            diag_display = diag_df[available_cols].copy()
            rename_map = {
                "retention_time": "tR, мин",
                "lri": "LRI расч.",
                "nearest": "Ближайший",
                "deviation": "ΔLRI",
                "reason": "Статус",
                "status": "Код",
            }
            diag_display.columns = [rename_map[c] for c in available_cols]
            st.dataframe(diag_display, width="stretch", hide_index=True)

            failed_statuses = {"auto_failed", "ambiguous", "no_match"}
            if "status" in diag_df.columns:
                failed = diag_df[diag_df["status"].isin(failed_statuses)]
                if not failed.empty:
                    st.warning(f"⚠️ Проблемных пиков: {len(failed)}")
                    for _, row in failed.iterrows():
                        rt = row.get("retention_time", 0.0)
                        reason = row.get("reason", "")
                        st.write(f"• tR={rt:.2f} мин — {reason}")

    # ============================================================
    # Расчёт
    # ============================================================
    st.markdown("---")

    valid_peaks = [
        p for p in st.session_state.peaks_data
        if (p.get("retention_time") or 0) > 0
        and (p.get("content") or 0) > 0
        and (p.get("name") or "").strip()
    ]

    if not valid_peaks:
        st.warning("⚠️ Нет данных для расчета. Заполните таблицу выше.")
        return

    try:
        result = calc.calculate(valid_peaks, normalize=True)
    except Exception as e:
        st.error(f"Ошибка расчета: {e}")
        return

    if "error" in result:
        st.error(result["error"])
        return

    # ── Ключевые показатели ───────────────────────────────────
    st.markdown("### 📊 Результаты расчета")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🔬 RON (Иссл.)", result["ron"])
    c2.metric("⚙️ MON (Мотор.)", result["mon"])
    c3.metric("📊 AKI (R+M)/2", result["aki"])
    c4.metric("📈 Чувствительность", result["sensitivity"])

    # ── ГОСТ ──────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📋 Соответствие ГОСТ 32513-2013")
    a_content = result["piona"].get("A", {}).get("content", 0.0)
    comparison_data = []
    for mark, std in GOST_STANDARDS.items():
        ron_ok = "✅" if result["ron"] >= std["RON_min"] else "❌"
        mon_ok = "✅" if result["mon"] >= std["MON_min"] else "❌"
        a_ok = "✅" if a_content <= std["A_max"] else "❌"
        comparison_data.append({
            "Марка": mark,
            f"RON ≥ {std['RON_min']}": f"{ron_ok} {result['ron']}",
            f"MON ≥ {std['MON_min']}": f"{mon_ok} {result['mon']}",
            f"Ароматика ≤ {std['A_max']}%": f"{a_ok} {a_content}",
        })
    st.dataframe(pd.DataFrame(comparison_data), width="stretch", hide_index=True)

    # ── PIONA ─────────────────────────────────────────────────
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
            st.plotly_chart(fig_pie, width="stretch")
    with tab2:
        piona_table = pd.DataFrame([
            {
                "Класс": CLASS_NAMES[k],
                "Содержание, %": v["content"],
                "Ср. RON": v["avg_ron"],
                "Ср. MON": v["avg_mon"],
            }
            for k, v in result["piona"].items() if v["content"] > 0
        ])
        st.dataframe(piona_table, width="stretch", hide_index=True)

    # ── Детализация ───────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🔬 Детализация по компонентам")
    groups_df = pd.DataFrame(result["groups"])
    if not groups_df.empty:
        groups_df["Класс"] = groups_df["class"].map(CLASS_NAMES)
        st.dataframe(
            groups_df[["name", "Класс", "content", "ron", "mon", "ron_contrib", "mon_contrib"]]
            .rename(columns={
                "name": "Компонент",
                "content": "Содерж., %",
                "ron": "RON",
                "mon": "MON",
                "ron_contrib": "Вклад RON",
                "mon_contrib": "Вклад MON",
            })
            .sort_values(["Класс", "content"], ascending=[True, False])
            .round(2),
            width="stretch",
            hide_index=True,
        )

    if result["unknown"]:
        st.warning("⚠️ Неидентифицированные компоненты (не учтены в расчете):")
        for u in result["unknown"]:
            st.write(f"• {u}")

    # ── Экспорт ───────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 💾 Экспорт результатов")
    export_df = pd.DataFrame([
        {"Параметр": "RON (Исследовательское)", "Значение": result["ron"]},
        {"Параметр": "MON (Моторное)", "Значение": result["mon"]},
        {"Параметр": "AKI (R+M)/2", "Значение": result["aki"]},
        {"Параметр": "Чувствительность (RON-MON)", "Значение": result["sensitivity"]},
        {"Параметр": "Сумма концентраций, %", "Значение": result["total_content"]},
    ])
    csv_bytes = export_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button("⬇️ Скачать отчет (CSV)", csv_bytes, "octane_report.csv", "text/csv")

    # ── Справка ───────────────────────────────────────────────
    with st.expander("📚 Справка по методике"):
        st.markdown("""
        **Методика расчета:**
        - Линейная модель смешения октановых чисел
        - PIONA-анализ по ASTM D6730 / ГОСТ Р 52709
        - LRI (линейный индекс удерживания) по Ван ден Дулу и Кратцу
          с корректным учётом несмежных якорей

        **Колонка:** HP-5 / DB-5 (5% фенил-метилполисилоксан)

        **Порядок элюирования C8-ароматики:**
        1. Этилбензол (LRI ~850)
        2. п-Ксилол + м-Ксилол (co-elution, LRI ~868)
        3. о-Ксилол (LRI ~885)

        **Ограничения модели:**
        - Линейная модель завышает RON для смесей с высокой долей ароматики;
          для практического применения рекомендуется калибровка по ASTM D2699/D2700.
        - Авто-идентификация требует ≥2 н-алканов-якорей с content > 0.
        - Групповые компоненты (i-C8, N-C7, A-C9+ и т.п.) в авто-ID не участвуют.

        **Нормативы:** ГОСТ 32513-2013 "Топлива моторные. Бензин неэтилированный"
        """)

    st.markdown("---")
    st.caption("© 2026 • PIONA + LRI • ASTM D6730 / ГОСТ 32513 / ГОСТ Р 52709")


if __name__ == "__main__":
    main()
