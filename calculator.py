"""
Модуль расчета октанового числа с автоидентификацией пиков по LRI.
Полная база данных компонентов бензина, отсортированная по индексу удерживания (HP-5/DB-5).

Исправления относительно первой версии:
  * Корректная формула LRI для несмежных якорей (учёт обоих углеродных номеров).
  * calculate_lri возвращает None при невозможности интерполяции.
  * Групповые компоненты исключены из автоидентификации (флаг is_group).
  * Разрешение коллизий по числу атомов углерода + флаг 'ambiguous'.
  * Защита от str(None) == 'None' повсюду.
  * Якоря берутся только из пиков с content > 0 и не групп.
  * В идентификации не перезаписываются валидные ручные имена.
  * Скорректированы табличные LRI (изооктан, 1-гептен, 1-октен, циклогексан).
  * Диагностика со status (auto_matched/manual_kept/manual_overwritten/auto_failed/ambiguous).
  * В calculate нормализуются и content/ron_contrib/mon_contrib в groups.
  * Защита от неизвестного class_name.
"""
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple


@dataclass
class ComponentProperties:
    class_name: str
    ron: float
    mon: float
    description: str
    table_lri: Optional[float] = None
    carbon_number: Optional[int] = None
    is_group: bool = False


VALID_CLASSES = ("P", "I", "O", "N", "A", "OXY")


class OctaneCalculator:
    """Калькулятор октанового числа с автоидентификацией по LRI."""

    def __init__(self):
        self.db: Dict[str, ComponentProperties] = {}
        self._load_database()

    # ==========================================================
    # БАЗА ДАННЫХ
    # ==========================================================
    def _load_database(self):
        # (name, class, ron, mon, desc, lri, carbon, is_group)
        data = [
            # ===== C4 =====
            ("Изобутан",       "I",  102.0,  97.0, "изобутан (2-метилпропан)",          385.0, 4, False),
            ("Изобутилен",     "O",   95.0,  80.0, "изобутилен (2-метилпропен)",        390.0, 4, False),
            ("1-бутен",        "O",   95.0,  80.0, "1-бутен",                           395.0, 4, False),
            ("н-бутан",        "P",   94.0,  91.0, "н-бутан (якорь C4)",                400.0, 4, False),
            ("транс-2-бутен",  "O",   95.0,  80.0, "транс-2-бутен",                     405.0, 4, False),
            ("цис-2-бутен",    "O",   95.0,  80.0, "цис-2-бутен",                       415.0, 4, False),

            # ===== OXY (легкие спирты) =====
            ("Метанол",        "OXY", 106.0,  92.0, "метанол",                          420.0, 1, False),
            ("Этанол",         "OXY", 109.0,  90.0, "этанол",                           460.0, 2, False),
            ("Трет-бутанол",   "OXY", 108.0,  90.0, "трет-бутанол (2-метил-2-пропанол)", 465.0, 4, False),

            # ===== C5 =====
            ("Изопентан",      "I",   92.0,  90.0, "изопентан (2-метилбутан)",          475.0, 5, False),
            ("2-метил-1-бутен","O",   90.0,  75.0, "2-метил-1-бутен",                   480.0, 5, False),
            ("1-пентен",       "O",   90.0,  75.0, "1-пентен",                          485.0, 5, False),
            ("Изопропанол",    "OXY", 105.0,  88.0, "изопропанол (2-пропанол)",          500.0, 3, False),
            ("н-пентан",       "P",   62.0,  62.0, "н-пентан (якорь C5)",               500.0, 5, False),
            ("Циклопентан",    "N",  101.0,  97.0, "циклопентан",                       515.0, 5, False),

            # ===== C6 =====
            ("2,2-диметилбутан","I",  85.0,  80.0, "2,2-диметилбутан",                  540.0, 6, False),
            ("2,3-диметилбутан","I",  85.0,  80.0, "2,3-диметилбутан",                  550.0, 6, False),
            ("Пропанол",       "OXY", 100.0,  85.0, "пропанол (1-пропанол)",             555.0, 3, False),
            ("2-метилпентан",  "I",   85.0,  80.0, "2-метилпентан",                     560.0, 6, False),
            ("3-метилпентан",  "I",   85.0,  80.0, "3-метилпентан",                     575.0, 6, False),
            ("1-гексен",       "O",   75.0,  63.0, "1-гексен",                          580.0, 6, False),
            ("н-гексан",       "P",   25.0,  26.0, "н-гексан (якорь C6)",               600.0, 6, False),
            ("Циклогексан",    "N",   95.0,  88.0, "циклогексан",                       630.0, 6, False),

            # ===== C7 =====
            ("2,2-диметилпентан","I",  75.0,  70.0, "2,2-диметилпентан",                630.0, 7, False),
            ("3,3-диметилпентан","I",  75.0,  70.0, "3,3-диметилпентан",                640.0, 7, False),
            ("2,4-диметилпентан","I",  75.0,  70.0, "2,4-диметилпентан",                645.0, 7, False),
            ("2-метилгексан",  "I",   75.0,  70.0, "2-метилгексан",                     650.0, 7, False),
            ("Бензол",         "A",   99.0,  91.0, "бензол (нормируется ≤1.0%)",        660.0, 6, False),
            ("2,3-диметилпентан","I",  75.0,  70.0, "2,3-диметилпентан",                655.0, 7, False),
            ("3-метилгексан",  "I",   75.0,  70.0, "3-метилгексан",                     665.0, 7, False),
            ("Бутанол",        "OXY", 95.0,  80.0, "бутанол (1-бутанол)",                670.0, 4, False),
            ("1-гептен",       "O",   60.0,  50.0, "1-гептен",                           695.0, 7, False),
            ("н-гептан",       "P",    0.0,   0.0, "н-гептан (якорь C7, RON=0)",         700.0, 7, False),

            # ===== C8 (алканы, нафтены, эфиры) =====
            ("Метилциклогексан","N",  80.0,  75.0, "метилциклогексан",                  725.0, 7, False),
            ("МТБЭ",           "OXY", 118.0, 101.0, "метил-трет-бутиловый эфир",         730.0, 5, False),
            ("2-метилгептан",  "I",   56.0,  56.0, "2-метилгептан",                     735.0, 8, False),
            ("3-метилгептан",  "I",   65.0,  62.0, "3-метилгептан",                     745.0, 8, False),
            ("Изооктан",       "I",  100.0, 100.0, "2,2,4-триметилпентан (RON=100)",     690.0, 8, False),
            ("Толуол",         "A",  120.0, 109.0, "толуол",                            760.0, 7, False),
            ("1-октен",        "O",   50.0,  40.0, "1-октен",                           790.0, 8, False),
            ("н-октан",        "P",  -10.0, -17.0, "н-октан (якорь C8)",                800.0, 8, False),
            ("ЭТБЭ",           "OXY", 118.0, 102.0, "этил-трет-бутиловый эфир",          820.0, 6, False),
            ("ТАМЭ",           "OXY", 115.0, 100.0, "трет-амилметилэфир",                830.0, 6, False),
            ("2-метилоктан",   "I",   45.0,  45.0, "2-метилоктан",                      830.0, 9, False),

            # ===== C8 ароматика =====
            ("Этилбензол",     "A",   98.0, 104.0, "этилбензол",                        850.0, 8, False),
            ("п-Ксилол",       "A",  116.0, 103.0, "п-ксилол (1,4-ДМБ)",                865.0, 8, False),
            ("м-/п-Ксилол",    "A",  117.0, 104.0, "м- + п-ксилол (co-elution)",        868.0, 8, False),
            ("м-Ксилол",       "A",  117.0, 104.0, "м-ксилол (1,3-ДМБ)",                870.0, 8, False),
            ("о-Ксилол",       "A",  117.0, 102.0, "о-ксилол (1,2-ДМБ)",                885.0, 8, False),

            # ===== C9+ =====
            ("н-нонан",        "P",  -20.0, -30.0, "н-нонан (якорь C9)",                900.0, 9, False),
            ("Кумол",          "A",  110.0, 100.0, "изопропилбензол (кумол)",           910.0, 9, False),
            ("Пропилбензол",   "A",  110.0, 100.0, "пропилбензол",                      920.0, 9, False),
            ("Мезитилен",      "A",  115.0, 105.0, "1,3,5-триметилбензол",              935.0, 9, False),
            ("Псевдокумол",    "A",  115.0, 105.0, "1,2,4-триметилбензол",              945.0, 9, False),
            ("Индан",          "A",  110.0, 100.0, "индан",                             960.0, 9, False),
            ("н-декан",        "P",  -30.0, -40.0, "н-декан (якорь C10)",              1000.0, 10, False),
            ("трет-Бутилбензол","A", 110.0, 100.0, "трет-бутилбензол",                 1010.0, 10, False),
            ("1,2,4,5-тетраметилбензол","A", 115.0, 105.0, "1,2,4,5-тетраметилбензол", 1015.0, 10, False),
            ("н-Бутилбензол",  "A",  110.0, 100.0, "н-бутилбензол",                    1030.0, 10, False),

            # ===== Групповые (только для ручного ввода / fallback, не для авто-ID) =====
            ("н-C4",   "P",   94.0,  91.0, "н-бутан (группа)",         400.0, 4, True),
            ("i-C4",   "I",  102.0,  97.0, "изобутан (группа)",        385.0, 4, True),
            ("i-C6",   "I",   85.0,  80.0, "C6-изомеры (средн.)",      560.0, 6, True),
            ("i-C7",   "I",   75.0,  70.0, "C7-изомеры (средн.)",      650.0, 7, True),
            ("i-C8",   "I",   70.0,  70.0, "C8-изомеры (средн.)",      740.0, 8, True),
            ("i-C9",   "I",   65.0,  60.0, "C9-изомеры (средн.)",      830.0, 9, True),
            ("i-C10",  "I",   55.0,  50.0, "C10-изомеры (средн.)",     920.0, 10, True),
            ("N-C5",   "N",  101.0,  97.0, "C5-нафтены (средн.)",      515.0, 5, True),
            ("N-C6",   "N",   95.0,  88.0, "C6-нафтены (средн.)",      620.0, 6, True),
            ("N-C7",   "N",   80.0,  75.0, "C7-нафтены (средн.)",      725.0, 7, True),
            ("N-C8",   "N",   70.0,  65.0, "C8-нафтены (средн.)",      825.0, 8, True),
            ("A-C9+",  "A",  112.0, 102.0, "C9+ ароматика (средн.)",   910.0, 9, True),
        ]

        for name, cls, ron, mon, desc, lri, carbon, is_group in data:
            self.db[name] = ComponentProperties(cls, ron, mon, desc, lri, carbon, is_group)

    # ==========================================================
    # LRI
    # ==========================================================
    def calculate_lri(
        self,
        retention_time: float,
        t_lower: float,
        t_upper: float,
        n_lower: int,
        n_upper: int,
    ) -> Optional[float]:
        """
        LRI по Ван ден Дулу и Кратцу между двумя (не обязательно соседними)
        якорями. Учитывает фактическую разницу углеродных чисел.
        Возвращает None при невозможности интерполяции.
        """
        if t_upper <= t_lower:
            return None
        if retention_time < t_lower or retention_time > t_upper:
            return None
        if n_upper <= n_lower:
            return None
        frac = (retention_time - t_lower) / (t_upper - t_lower)
        return 100.0 * (n_lower + frac * (n_upper - n_lower))

    # ==========================================================
    # ЯКОРЯ
    # ==========================================================
    def get_n_alkanes(self, peaks: List[Dict]) -> Dict[int, float]:
        """
        Извлечение н-алканов из списка пиков для интерполяции.
        Берутся только пики с непустым именем, content > 0 и не группы.
        """
        n_alkanes: Dict[int, float] = {}
        for peak in peaks:
            name = str(peak.get("name") or "").strip()
            if not name or name not in self.db:
                continue
            props = self.db[name]
            if not (name.startswith("н-") and props.carbon_number and not props.is_group):
                continue
            try:
                rt = float(peak.get("retention_time") or 0)
                content = float(peak.get("content") or 0)
            except (ValueError, TypeError):
                continue
            if rt <= 0 or content <= 0:
                continue
            n_alkanes[props.carbon_number] = rt
        return n_alkanes

    def describe_anchors(self, peaks: List[Dict]) -> str:
        """Краткое описание использованных якорей."""
        n_alkanes = self.get_n_alkanes(peaks)
        if not n_alkanes:
            return "нет"
        return ", ".join(f"C{c}@{n_alkanes[c]:.2f}" for c in sorted(n_alkanes))

    # ==========================================================
    # ИДЕНТИФИКАЦИЯ
    # ==========================================================
    def identify_peak(
        self,
        retention_time: float,
        n_alkanes: Dict[int, float],
        tolerance: float = 10.0,
    ) -> Dict:
        """
        Идентификация одного пика с полной диагностикой.
        Ключи: name, lri, nearest, deviation, reason, status.
        status ∈ {auto_matched, auto_failed, ambiguous, no_match}
        """
        result = {
            "name": None,
            "lri": None,
            "nearest": None,
            "deviation": None,
            "reason": "",
            "status": "no_match",
        }

        if not n_alkanes or len(n_alkanes) < 2:
            result["reason"] = "⚠️ Нужно ≥2 н-алкана (с content>0)"
            return result

        sorted_carbons = sorted(n_alkanes.keys())
        n_lower = n_upper = None
        t_lower = t_upper = None

        for c in sorted_carbons:
            if n_alkanes[c] <= retention_time:
                n_lower = c
                t_lower = n_alkanes[c]
            elif n_alkanes[c] > retention_time and t_upper is None:
                n_upper = c
                t_upper = n_alkanes[c]
                break

        if n_lower is None:
            result["reason"] = (
                f"⚠️ tR={retention_time:.2f} < первого якоря "
                f"({n_alkanes[sorted_carbons[0]]:.2f})"
            )
            return result
        if n_upper is None:
            result["reason"] = (
                f"⚠️ tR={retention_time:.2f} > последнего якоря "
                f"({n_alkanes[sorted_carbons[-1]]:.2f})"
            )
            return result

        lri = self.calculate_lri(retention_time, t_lower, t_upper, n_lower, n_upper)
        if lri is None:
            result["reason"] = "⚠️ Ошибка интерполяции LRI"
            return result

        result["lri"] = round(lri, 1)
        expected_c = round(lri / 100.0)

        # Кандидаты: без групповых, с сортировкой по (ΔLRI, ΔC)
        candidates = []
        for name, props in self.db.items():
            if props.table_lri is None or props.is_group:
                continue
            dev = abs(lri - props.table_lri)
            c_dev = abs((props.carbon_number or 0) - expected_c)
            candidates.append((dev, c_dev, name))

        if not candidates:
            result["reason"] = "⚠️ База данных пуста"
            return result

        candidates.sort(key=lambda x: (x[0], x[1]))
        best_dev, _, best_name = candidates[0]
        result["nearest"] = best_name
        result["deviation"] = round(best_dev, 1)

        if best_dev > tolerance:
            result["status"] = "auto_failed"
            result["reason"] = f"⚠️ ΔLRI={best_dev:.1f} > допуска {tolerance}"
            return result

        # Неоднозначность: два кандидата в допуске с близкими отклонениями
        ambiguous = [c for c in candidates[1:]
                     if c[0] <= tolerance and abs(c[0] - best_dev) < 2.0]
        if ambiguous:
            names = [best_name] + [a[2] for a in ambiguous[:2]]
            result["status"] = "ambiguous"
            result["reason"] = f"⚠️ Неоднозначно: {', '.join(names)}"
            return result

        result["name"] = best_name
        result["status"] = "auto_matched"
        result["reason"] = "✅ Идентифицирован"
        return result

    def identify_all_peaks(
        self,
        peaks: List[Dict],
        tolerance: float = 10.0,
        overwrite: bool = False,
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Идентификация всех пиков. Мутирует peaks['name'] при необходимости.
        Ручные имена, совпадающие с LRI, не перезаписываются даже при overwrite=True.
        """
        n_alkanes = self.get_n_alkanes(peaks)
        diagnostics: List[Dict] = []

        for peak in peaks:
            name = str(peak.get("name") or "").strip()
            try:
                rt = float(peak.get("retention_time") or 0)
                content = float(peak.get("content") or 0)
            except (ValueError, TypeError):
                continue
            if rt <= 0 or content <= 0:
                continue

            diag = self.identify_peak(rt, n_alkanes, tolerance)
            diag["peak_name"] = name if name else "(пусто)"
            diag["retention_time"] = rt

            # Проверка валидности ручного имени
            manual_dev = None
            manual_valid = False
            if name and name in self.db:
                props = self.db[name]
                if props.table_lri is not None and diag["lri"] is not None:
                    manual_dev = abs(diag["lri"] - props.table_lri)
                    manual_valid = manual_dev <= tolerance

            # 1) Не перезаписываем, если overwrite=False
            if name and not overwrite:
                if manual_dev is not None and not manual_valid:
                    diag["status"] = "manual_kept"
                    diag["reason"] = (
                        f"⚠️ Вручную: {name} (ΔLRI={manual_dev:.1f}, вероятна ошибка)"
                    )
                else:
                    diag["status"] = "manual_kept"
                    diag["reason"] = f"✋ Вручную: {name}"
                diagnostics.append(diag)
                continue

            # 2) overwrite=True, но ручное имя валидно — тоже оставляем
            if name and overwrite and manual_valid:
                diag["status"] = "manual_kept"
                diag["reason"] = f"✋ Вручную (совпадает с LRI): {name}"
                diagnostics.append(diag)
                continue

            # 3) Авто-ID
            if diag["status"] == "auto_matched":
                if name and name != diag["name"]:
                    diag["status"] = "manual_overwritten"
                    diag["reason"] = f"🔄 {name} → {diag['name']}"
                peak["name"] = diag["name"]

            diagnostics.append(diag)

        return peaks, diagnostics

    # ==========================================================
    # РАСЧЁТ ОКТАНОВОГО ЧИСЛА
    # ==========================================================
    def calculate(self, chromatogram: List[Dict], normalize: bool = True) -> Dict:
        total_content = 0.0
        total_ron = 0.0
        total_mon = 0.0
        piona = {k: 0.0 for k in VALID_CLASSES}
        piona_ron = {k: 0.0 for k in VALID_CLASSES}
        piona_mon = {k: 0.0 for k in VALID_CLASSES}
        groups: List[Dict] = []
        unknown: List[str] = []

        for entry in chromatogram:
            name = str(entry.get("name") or "").strip()
            try:
                content = float(entry.get("content") or 0)
            except (ValueError, TypeError):
                continue
            if content <= 0 or not name:
                continue
            if name not in self.db:
                unknown.append(f"{name} ({content:.2f}%)")
                continue
            props = self.db[name]
            if props.class_name not in piona:
                unknown.append(f"{name} (неизвестный класс '{props.class_name}')")
                continue

            groups.append({
                "name": name,
                "class": props.class_name,
                "content": content,
                "ron": props.ron,
                "mon": props.mon,
                "ron_contrib": content * props.ron,
                "mon_contrib": content * props.mon,
            })
            total_content += content
            total_ron += content * props.ron
            total_mon += content * props.mon
            piona[props.class_name] += content
            piona_ron[props.class_name] += content * props.ron
            piona_mon[props.class_name] += content * props.mon

        if total_content == 0:
            return {"error": "Нет данных для расчета"}

        if normalize:
            k = 100.0 / total_content
            total_ron *= k
            total_mon *= k
            for cls in piona:
                piona[cls] *= k
                piona_ron[cls] *= k
                piona_mon[cls] *= k
            # Синхронизируем groups с нормализованной шкалой
            for g in groups:
                g["content"] *= k
                g["ron_contrib"] *= k
                g["mon_contrib"] *= k
            total_content = 100.0

        ron = total_ron / total_content
        mon = total_mon / total_content

        piona_avg = {
            cls: {
                "content": round(piona[cls], 2),
                "avg_ron": round(piona_ron[cls] / piona[cls], 1) if piona[cls] > 0 else 0,
                "avg_mon": round(piona_mon[cls] / piona[cls], 1) if piona[cls] > 0 else 0,
            }
            for cls in piona
        }

        return {
            "groups": groups,
            "piona": piona_avg,
            "total_content": round(total_content, 2),
            "ron": round(ron, 1),
            "mon": round(mon, 1),
            "aki": round((ron + mon) / 2, 1),
            "sensitivity": round(ron - mon, 1),
            "unknown": unknown,
        }
