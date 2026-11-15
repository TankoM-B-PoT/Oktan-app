"""
Модуль расчета октанового числа с автоидентификацией пиков по LRI.
Полная база данных компонентов бензина, отсортированная по индексу удерживания (HP-5/DB-5).
"""
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple


@dataclass
class ComponentProperties:
    """Свойства компонента/группы"""
    class_name: str           # P, I, O, N, A, OXY
    ron: float                # Исследовательское октановое число
    mon: float                # Моторное октановое число
    description: str          # Описание
    table_lri: Optional[float] = None  # Табличный LRI (колонка HP-5/DB-5)
    carbon_number: Optional[int] = None  # Число атомов углерода


class OctaneCalculator:
    """Калькулятор октанового числа с автоидентификацией"""

    def __init__(self):
        self.db: Dict[str, ComponentProperties] = {}
        self._load_database()

    def _load_database(self):
        """
        Полная база данных компонентов бензина.
        Отсортирована по LRI (колонка HP-5/DB-5, 5% фенил-метилполисилоксан).
        """
        data = [
            # ==========================================================
            # C4 ФРАКЦИЯ
            # ==========================================================
            ("Изобутан",       "I",  102.0,  97.0, "изобутан (2-метилпропан)",      385.0, 4),
            ("Изобутилен",     "O",   95.0,  80.0, "изобутилен (2-метилпропен)",    390.0, 4),
            ("1-бутен",        "O",   95.0,  80.0, "1-бутен",                       395.0, 4),
            ("н-бутан",        "P",   94.0,  91.0, "н-бутан (якорь C4)",            400.0, 4),
            ("транс-2-бутен",  "O",   95.0,  80.0, "транс-2-бутен",                 405.0, 4),
            ("цис-2-бутен",    "O",   95.0,  80.0, "цис-2-бутен",                   415.0, 4),

            # ==========================================================
            # КИСЛОРОДСОДЕРЖАЩИЕ (ЛЕГКИЕ СПИРТЫ)
            # ==========================================================
            ("Метанол",        "OXY", 106.0,  92.0, "метанол",                      420.0, 1),
            ("Этанол",         "OXY", 109.0,  90.0, "этанол",                       460.0, 2),
            ("Трет-бутанол",   "OXY", 108.0,  90.0, "трет-бутанол (2-метил-2-пропанол)", 465.0, 4),

            # ==========================================================
            # C5 ФРАКЦИЯ
            # ==========================================================
            ("Изопентан",      "I",   92.0,  90.0, "изопентан (2-метилбутан)",       475.0, 5),
            ("2-метил-1-бутен","O",   90.0,  75.0, "2-метил-1-бутен",                480.0, 5),
            ("1-пентен",       "O",   90.0,  75.0, "1-пентен",                       485.0, 5),
            ("Изопропанол",    "OXY", 105.0,  88.0, "изопропанол (2-пропанол)",       500.0, 3),
            ("н-пентан",       "P",   62.0,  62.0, "н-пентан (якорь C5)",            500.0, 5),
            ("Циклопентан",    "N",  101.0,  97.0, "циклопентан",                    515.0, 5),

            # ==========================================================
            # C6 ФРАКЦИЯ
            # ==========================================================
            ("2,2-диметилбутан","I",  85.0,  80.0, "2,2-диметилбутан",               540.0, 6),
            ("2,3-диметилбутан","I",  85.0,  80.0, "2,3-диметилбутан",               550.0, 6),
            ("Пропанол",       "OXY", 100.0,  85.0, "пропанол (1-пропанол)",          555.0, 3),
            ("2-метилпентан",  "I",   85.0,  80.0, "2-метилпентан",                  560.0, 6),
            ("3-метилпентан",  "I",   85.0,  80.0, "3-метилпентан",                  575.0, 6),
            ("1-гексен",       "O",   75.0,  63.0, "1-гексен",                       580.0, 6),
            ("н-гексан",       "P",   25.0,  26.0, "н-гексан (якорь C6)",            600.0, 6),
            ("Циклогексан",    "N",   95.0,  88.0, "циклогексан",                    620.0, 6),

            # ==========================================================
            # C7 ФРАКЦИЯ
            # ==========================================================
            ("2,2-диметилпентан","I",  75.0,  70.0, "2,2-диметилпентан",             630.0, 7),
            ("3,3-диметилпентан","I",  75.0,  70.0, "3,3-диметилпентан",             640.0, 7),
            ("2,4-диметилпентан","I",  75.0,  70.0, "2,4-диметилпентан",             645.0, 7),
            ("2-метилгексан",  "I",   75.0,  70.0, "2-метилгексан",                  650.0, 7),
            ("Бензол",         "A",   99.0,  91.0, "бензол (нормируется ≤1.0%)",     650.0, 6),
            ("2,3-диметилпентан","I",  75.0,  70.0, "2,3-диметилпентан",             655.0, 7),
            ("3-метилгексан",  "I",   75.0,  70.0, "3-метилгексан",                  665.0, 7),
            ("Бутанол",        "OXY",  95.0,  80.0, "бутанол (1-бутанол)",            670.0, 4),
            ("1-гептен",       "O",   60.0,  50.0, "1-гептен",                       675.0, 7),
            ("н-гептан",       "P",    0.0,   0.0, "н-гептан (якорь C7, RON=0)",     700.0, 7),

            # ==========================================================
            # C8 ФРАКЦИЯ (АЛКАНЫ, НАФТЕНЫ, ЭФИРЫ)
            # ==========================================================
            ("Метилциклогексан","N",  80.0,  75.0, "метилциклогексан",               725.0, 7),
            ("МТБЭ",           "OXY", 118.0, 101.0, "метил-трет-бутиловый эфир",      730.0, 5),
            ("2-метилгептан",  "I",   56.0,  56.0, "2-метилгептан",                  735.0, 8),
            ("3-метилгептан",  "I",   65.0,  62.0, "3-метилгептан",                  745.0, 8),
            ("Изооктан",       "I",  100.0, 100.0, "2,2,4-триметилпентан (RON=100)", 750.0, 8),
            ("Толуол",         "A",  120.0, 109.0, "толуол",                         760.0, 7),
            ("1-октен",        "O",   50.0,  40.0, "1-октен",                        770.0, 8),
            ("н-октан",        "P",  -10.0, -17.0, "н-октан (якорь C8)",             800.0, 8),
            ("ЭТБЭ",           "OXY", 118.0, 102.0, "этил-трет-бутиловый эфир",       820.0, 6),
            ("ТАМЭ",           "OXY", 115.0, 100.0, "трет-амилметилэфир",             830.0, 6),
            ("2-метилоктан",   "I",   45.0,  45.0, "2-метилоктан",                   830.0, 9),

            # ==========================================================
            # C8 АРОМАТИКА
            # ==========================================================
            ("Этилбензол",     "A",   98.0, 104.0, "этилбензол",                     850.0, 8),
            ("п-Ксилол",       "A",  116.0, 103.0, "п-ксилол (1,4-ДМБ)",             865.0, 8),
            ("м-Ксилол",       "A",  117.0, 104.0, "м-ксилол (1,3-ДМБ)",             870.0, 8),
            ("м-/п-Ксилол",    "A",  117.0, 104.0, "м- + п-ксилол (co-elution)",     868.0, 8),
            ("о-Ксилол",       "A",  117.0, 102.0, "о-ксилол (1,2-ДМБ)",             885.0, 8),

            # ==========================================================
            # C9+ ФРАКЦИЯ
            # ==========================================================
            ("н-нонан",        "P",  -20.0, -30.0, "н-нонан (якорь C9)",             900.0, 9),
            ("Кумол",          "A",  110.0, 100.0, "изопропилбензол (кумол)",        910.0, 9),
            ("Пропилбензол",   "A",  110.0, 100.0, "пропилбензол",                   920.0, 9),
            ("Мезитилен",      "A",  115.0, 105.0, "1,3,5-триметилбензол",           935.0, 9),
            ("Псевдокумол",    "A",  115.0, 105.0, "1,2,4-триметилбензол",           945.0, 9),
            ("Индан",          "A",  110.0, 100.0, "индан",                          960.0, 9),
            ("н-декан",        "P",  -30.0, -40.0, "н-декан (якорь C10)",           1000.0, 10),
            ("трет-Бутилбензол","A", 110.0, 100.0, "трет-бутилбензол",              1010.0, 10),
            ("1,2,4,5-тетраметилбензол","A", 115.0, 105.0, "1,2,4,5-тетраметилбензол", 1015.0, 10),
            ("н-Бутилбензол",  "A",  110.0, 100.0, "н-бутилбензол",                 1030.0, 10),

            # ==========================================================
            # ГРУППОВЫЕ КОМПОНЕНТЫ (для случаев, когда пики не разделены)
            # ==========================================================
            ("н-C4",   "P",   94.0,  91.0, "н-бутан (группа)",              400.0, 4),
            ("i-C4",   "I",  102.0,  97.0, "изобутан (группа)",             385.0, 4),
            ("i-C6",   "I",   85.0,  80.0, "C6-изомеры (средн.)",           560.0, 6),
            ("i-C7",   "I",   75.0,  70.0, "C7-изомеры (средн.)",           650.0, 7),
            ("i-C8",   "I",   70.0,  70.0, "C8-изомеры (средн.)",           740.0, 8),
            ("i-C9",   "I",   65.0,  60.0, "C9-изомеры (средн.)",           830.0, 9),
            ("i-C10",  "I",   55.0,  50.0, "C10-изомеры (средн.)",          920.0, 10),
            ("N-C5",   "N",  101.0,  97.0, "C5-нафтены (средн.)",           515.0, 5),
            ("N-C6",   "N",   95.0,  88.0, "C6-нафтены (средн.)",           620.0, 6),
            ("N-C7",   "N",   80.0,  75.0, "C7-нафтены (средн.)",           725.0, 7),
            ("N-C8",   "N",   70.0,  65.0, "C8-нафтены (средн.)",           825.0, 8),
            ("A-C9+",  "A",  112.0, 102.0, "C9+ ароматика (средн.)",        910.0, 9),
        ]

        for name, cls, ron, mon, desc, lri, carbon in data:
            self.db[name] = ComponentProperties(cls, ron, mon, desc, lri, carbon)

    # ==========================================================
    # 🧮 РАСЧЕТ LRI
    # ==========================================================
    def calculate_lri(self, retention_time: float, t_n: float, t_n1: float, n_carbon: int) -> float:
        """Расчет LRI по формуле Ван ден Дула и Кратца (программируемая температура)"""
        if t_n1 <= t_n or retention_time < t_n:
            return 0.0
        return 100.0 * (n_carbon + (retention_time - t_n) / (t_n1 - t_n))

    def get_n_alkanes(self, peaks: List[Dict]) -> Dict[int, float]:
        """Извлечение н-алканов из списка пиков для интерполяции"""
        n_alkanes = {}
        for peak in peaks:
            name = str(peak.get("name", "")).strip()
            rt = peak.get("retention_time")
            if rt is None or name not in self.db:
                continue
            try:
                rt = float(rt)
            except (ValueError, TypeError):
                continue
            if rt <= 0:
                continue
            props = self.db[name]
            if name.startswith("н-") and props.carbon_number:
                n_alkanes[props.carbon_number] = rt
        return n_alkanes

    # ==========================================================
    # 🔍 ИДЕНТИФИКАЦИЯ ПИКОВ
    # ==========================================================
    def identify_peak(self, retention_time: float, n_alkanes: Dict[int, float],
                      tolerance: float = 10.0) -> Dict:
        """
        Идентификация одного пика с полной диагностикой.
        Возвращает: {'name', 'lri', 'nearest', 'deviation', 'reason'}
        """
        result = {
            'name': None,
            'lri': None,
            'nearest': None,
            'deviation': None,
            'reason': ''
        }

        if not n_alkanes or len(n_alkanes) < 2:
            result['reason'] = '⚠️ Нужно ≥2 н-алканов в таблице'
            return result

        sorted_carbons = sorted(n_alkanes.keys())
        t_n = None
        t_n1 = None
        n_carbon = 0

        for c in sorted_carbons:
            if n_alkanes[c] <= retention_time:
                t_n = n_alkanes[c]
                n_carbon = c
            elif n_alkanes[c] > retention_time and t_n1 is None:
                t_n1 = n_alkanes[c]
                break

        if t_n is None:
            result['reason'] = f'⚠️ tR={retention_time} меньше первого н-алкана ({n_alkanes[min(sorted_carbons)]})'
            return result
        if t_n1 is None:
            result['reason'] = f'⚠️ tR={retention_time} больше последнего н-алкана ({n_alkanes[max(sorted_carbons)]})'
            return result

        calculated_lri = self.calculate_lri(retention_time, t_n, t_n1, n_carbon)
        result['lri'] = round(calculated_lri, 1)

        # Поиск ближайшего компонента
        best_match = None
        min_deviation = float('inf')
        for name, props in self.db.items():
            if props.table_lri is None:
                continue
            deviation = abs(calculated_lri - props.table_lri)
            if deviation < min_deviation:
                min_deviation = deviation
                best_match = name

        result['nearest'] = best_match
        result['deviation'] = round(min_deviation, 1)

        if min_deviation <= tolerance:
            result['name'] = best_match
            result['reason'] = '✅ Идентифицирован'
        else:
            result['reason'] = f'⚠️ ΔLRI={min_deviation:.1f} > допуска {tolerance}'

        return result

    def identify_all_peaks(self, peaks: List[Dict], tolerance: float = 10.0,
                           overwrite: bool = False) -> Tuple[List[Dict], List[Dict]]:
        """Идентификация всех пиков. Возвращает (обновлённые пики, список диагностик)."""
        n_alkanes = self.get_n_alkanes(peaks)
        diagnostics = []

        for peak in peaks:
            name = str(peak.get("name", "")).strip()
            rt = peak.get("retention_time")
            content = peak.get("content")

            try:
                rt = float(rt) if rt else 0
                content = float(content) if content else 0
            except (ValueError, TypeError):
                continue

            if rt <= 0 or content <= 0:
                continue

            if name and not overwrite:
                diag = self.identify_peak(rt, n_alkanes, tolerance)
                diag['peak_name'] = name
                diag['retention_time'] = rt
                diagnostics.append(diag)
                continue

            diag = self.identify_peak(rt, n_alkanes, tolerance)
            diag['peak_name'] = name if name else '(пусто)'
            diag['retention_time'] = rt

            if diag['name']:
                peak['name'] = diag['name']

            diagnostics.append(diag)

        return peaks, diagnostics

    # ==========================================================
    # 🧮 РАСЧЕТ ОКТАНОВОГО ЧИСЛА
    # ==========================================================
    def calculate(self, chromatogram: List[Dict], normalize: bool = True) -> Dict:
        """Расчет октанового числа по данным хроматограммы"""
        total_content = 0.0
        total_ron = 0.0
        total_mon = 0.0
        piona = {"P": 0.0, "I": 0.0, "O": 0.0, "N": 0.0, "A": 0.0, "OXY": 0.0}
        piona_ron = {k: 0.0 for k in piona}
        piona_mon = {k: 0.0 for k in piona}
        groups = []
        unknown = []

        for entry in chromatogram:
            name = str(entry.get("name", "")).strip()
            try:
                content = float(entry.get("content", 0))
            except (ValueError, TypeError):
                continue
            if content <= 0 or not name:
                continue
            if name not in self.db:
                unknown.append(f"{name} ({content:.2f}%)")
                continue
            props = self.db[name]
            groups.append({
                "name": name, "class": props.class_name,
                "content": content, "ron": props.ron, "mon": props.mon,
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

        if normalize and total_content > 0:
            k = 100.0 / total_content
            total_ron *= k
            total_mon *= k
            for cls in piona:
                piona[cls] *= k
                piona_ron[cls] *= k
                piona_mon[cls] *= k
            total_content = 100.0

        ron = total_ron / total_content
        mon = total_mon / total_content

        piona_avg = {}
        for cls in piona:
            piona_avg[cls] = {
                "content": round(piona[cls], 2),
                "avg_ron": round(piona_ron[cls] / piona[cls], 1) if piona[cls] > 0 else 0,
                "avg_mon": round(piona_mon[cls] / piona[cls], 1) if piona[cls] > 0 else 0,
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
