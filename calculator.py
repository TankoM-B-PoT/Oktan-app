"""
Модуль расчета октанового числа бензина по данным хроматографии.
PIONA-анализ + детализация по изомерам C8-C10.
Проверка разметки по линейному индексу удерживания (LRI).
"""
from dataclasses import dataclass
from typing import List, Dict, Optional


@dataclass
class ComponentProperties:
    """Свойства компонента/группы"""
    class_name: str           # P, I, O, N, A, OXY
    ron: float                # Исследовательское октановое число
    mon: float                # Моторное октановое число
    description: str          # Описание
    table_lri: Optional[float] = None  # Табличный LRI (для непрогр. температуры = индекс Ковача)
    carbon_number: Optional[int] = None  # Число атомов углерода (для н-алканов и ароматики)


class OctaneCalculator:
    """Основной класс для расчета октанового числа и проверки LRI"""

    def __init__(self):
        self.db: Dict[str, ComponentProperties] = {}
        self._load_database()

    def _load_database(self):
        """Загрузка базы данных компонентов"""
        data = [
            # ==========================================================
            # 🎯 ОПОРНЫЕ ПИКИ (Anchor Peaks)
            # ==========================================================
            ("н-Пентан",     "P",   62.0,  62.0, "н-пентан",                500.0, 5),
            ("Изопентан",    "I",   92.0,  90.0, "изопентан (2-метилбутан)", 475.0, 5),
            ("н-Гексан",     "P",   25.0,  26.0, "н-гексан",                600.0, 6),
            ("Бензол",       "A",   99.0,  91.0, "бензол (нормируется ГОСТ)", 650.0, 6),
            ("н-Гептан",     "P",    0.0,   0.0, "н-гептан (стандарт RON=0)", 700.0, 7),
            ("Толуол",       "A",  120.0, 109.0, "толуол",                  760.0, 7),
            ("н-Октан",      "P",  -10.0, -17.0, "н-октан",                 800.0, 8),
            ("Изооктан",     "I",  100.0, 100.0, "2,2,4-ТМП (стандарт RON=100)", 750.0, 8),
            ("Этилбензол",   "A",   98.0, 104.0, "этилбензол",              850.0, 8),
            ("п-Ксилол",     "A",  116.0, 103.0, "п-ксилол (1,4-ДМБ)",      865.0, 8),
            ("м-Ксилол",     "A",  117.0, 104.0, "м-ксилол (1,3-ДМБ)",      870.0, 8),
            ("м-/п-Ксилол",  "A",  117.0, 104.0, "м-ксилол + п-ксилол (co-elution)", 868.0, 8),
            ("о-Ксилол",     "A",  117.0, 102.0, "о-ксилол (1,2-ДМБ)",      885.0, 8),
            ("н-Нонан",      "P",  -20.0, -30.0, "н-нонан",                 900.0, 9),
            ("н-Декан",      "P",  -30.0, -40.0, "н-декан",                1000.0, 10),
            ("н-Ундекан+",   "P",  -45.0, -55.0, "н-C11+ (тяжелые н-алканы)", 1100.0, 11),

            # ==========================================================
            # 📦 ГРУППОВЫЕ КОМПОНЕНТЫ (PIONA без детализации)
            # ==========================================================
            ("н-C4",   "P",   94.0,  91.0, "н-бутан",                   400.0, 4),
            ("i-C4",   "I",  102.0,  97.0, "изобутан",                  385.0, 4),
            ("i-C6",   "I",   85.0,  80.0, "C6-изомеры (средние)",      560.0, 6),
            ("i-C7",   "I",   75.0,  70.0, "C7-изомеры (средние)",      650.0, 7),
            ("i-C8",   "I",   70.0,  70.0, "C8-изомеры (средние)",      740.0, 8),
            ("i-C9",   "I",   65.0,  60.0, "C9-изомеры (средние)",      830.0, 9),
            ("i-C10",  "I",   55.0,  50.0, "C10-изомеры (средние)",     920.0, 10),
            ("i-C11+", "I",   40.0,  35.0, "C11+-изомеры",             1010.0, 11),

            # ==========================================================
            # 🔬 ИЗОМЕРЫ ОКТАНА (C8)
            # ==========================================================
            ("2-MeC7",          "I",  56.0,  56.0, "2-метилгептан",           735.0, 8),
            ("3-MeC7",          "I",  65.0,  62.0, "3-метилгептан",           745.0, 8),
            ("4-MeC7",          "I",  68.0,  65.0, "4-метилгептан",           750.0, 8),
            ("2,2-diMeC6",      "I",  80.0,  75.0, "2,2-диметилгексан",       720.0, 8),
            ("2,3-diMeC6",      "I",  78.0,  73.0, "2,3-диметилгексан",       730.0, 8),
            ("2,4-diMeC6",      "I",  82.0,  78.0, "2,4-диметилгексан",       735.0, 8),
            ("2,5-diMeC6",      "I",  85.0,  80.0, "2,5-диметилгексан",       740.0, 8),
            ("3,3-diMeC6",      "I",  75.0,  70.0, "3,3-диметилгексан",       725.0, 8),
            ("3,4-diMeC6",      "I",  76.0,  72.0, "3,4-диметилгексан",       738.0, 8),
            ("3-Et-2-MeC5",     "I",  88.0,  82.0, "3-этил-2-метилпентан",    745.0, 8),
            ("3-Et-3-MeC5",     "I",  90.0,  85.0, "3-этил-3-метилпентан",    750.0, 8),
            ("2,2,3-triMeC5",   "I",  95.0,  90.0, "2,2,3-триметилпентан",    740.0, 8),
            ("2,2,4-triMeC5",   "I", 100.0, 100.0, "2,2,4-триметилпентан",    750.0, 8),
            ("2,3,3-triMeC5",   "I",  92.0,  87.0, "2,3,3-триметилпентан",    748.0, 8),
            ("2,3,4-triMeC5",   "I",  88.0,  83.0, "2,3,4-триметилпентан",    752.0, 8),
            ("3-Et-2,2-diMeC4", "I", 105.0,  98.0, "3-этил-2,2-диметилбутан", 742.0, 8),
            ("3-Et-2,3-diMeC4", "I", 102.0,  95.0, "3-этил-2,3-диметилбутан", 755.0, 8),
            ("2,2,3,3-tetraMeC4", "I", 110.0, 105.0, "2,2,3,3-тетраметилбутан", 760.0, 8),

            # ==========================================================
            # 🔬 ИЗОМЕРЫ НОНАНА (C9)
            # ==========================================================
            ("2-MeC8",        "I",  45.0,  45.0, "2-метилоктан",         830.0, 9),
            ("3-MeC8",        "I",  55.0,  52.0, "3-метилоктан",         840.0, 9),
            ("4-MeC8",        "I",  60.0,  57.0, "4-метилоктан",         845.0, 9),
            ("2,2-diMeC7",    "I",  70.0,  65.0, "2,2-диметилгептан",    815.0, 9),
            ("2,3-diMeC7",    "I",  72.0,  68.0, "2,3-диметилгептан",    825.0, 9),
            ("2,4-diMeC7",    "I",  75.0,  70.0, "2,4-диметилгептан",    830.0, 9),
            ("2,5-diMeC7",    "I",  78.0,  73.0, "2,5-диметилгептан",    835.0, 9),
            ("3,3-diMeC7",    "I",  68.0,  63.0, "3,3-диметилгептан",    820.0, 9),
            ("3,4-diMeC7",    "I",  70.0,  66.0, "3,4-диметилгептан",    832.0, 9),
            ("4,4-diMeC7",    "I",  72.0,  67.0, "4,4-диметилгептан",    838.0, 9),
            ("2,2,4-triMeC6", "I",  85.0,  80.0, "2,2,4-триметилгексан", 828.0, 9),
            ("2,3,4-triMeC6", "I",  82.0,  77.0, "2,3,4-триметилгексан", 835.0, 9),
            ("2,2,5-triMeC6", "I",  88.0,  83.0, "2,2,5-триметилгексан", 832.0, 9),
            ("3-Et-2-MeC6",   "I",  80.0,  75.0, "3-этил-2-метилгексан", 838.0, 9),
            ("3-Et-3-MeC6",   "I",  85.0,  80.0, "3-этил-3-метилгексан", 842.0, 9),
            ("3-Et-4-MeC6",   "I",  82.0,  77.0, "3-этил-4-метилгексан", 845.0, 9),

            # ==========================================================
            # 🔬 ИЗОМЕРЫ ДЕКАНА (C10)
            # ==========================================================
            ("2-MeC9",        "I",  38.0,  38.0, "2-метилнонан",         920.0, 10),
            ("3-MeC9",        "I",  48.0,  45.0, "3-метилнонан",         930.0, 10),
            ("4-MeC9",        "I",  52.0,  49.0, "4-метилнонан",         935.0, 10),
            ("5-MeC9",        "I",  55.0,  52.0, "5-метилнонан",         938.0, 10),
            ("2,2-diMeC8",    "I",  65.0,  60.0, "2,2-диметилоктан",     915.0, 10),
            ("2,3-diMeC8",    "I",  68.0,  63.0, "2,3-диметилоктан",     925.0, 10),
            ("2,4-diMeC8",    "I",  70.0,  65.0, "2,4-диметилоктан",     930.0, 10),
            ("2,5-diMeC8",    "I",  72.0,  67.0, "2,5-диметилоктан",     935.0, 10),
            ("3,3-diMeC8",    "I",  62.0,  57.0, "3,3-диметилоктан",     920.0, 10),
            ("3,4-diMeC8",    "I",  65.0,  60.0, "3,4-диметилоктан",     932.0, 10),
            ("2,2,4-triMeC7", "I",  78.0,  73.0, "2,2,4-триметилгептан", 928.0, 10),
            ("2,3,4-triMeC7", "I",  75.0,  70.0, "2,3,4-триметилгептан", 935.0, 10),
            ("2,2,5-triMeC7", "I",  80.0,  75.0, "2,2,5-триметилгептан", 932.0, 10),
            ("2,3,5-triMeC7", "I",  77.0,  72.0, "2,3,5-триметилгептан", 938.0, 10),

            # ==========================================================
            # 🌀 ОЛЕФИНЫ
            # ==========================================================
            ("C4-ол",  "O",  95.0,  80.0, "бутены",   390.0, 4),
            ("C5-ол",  "O",  90.0,  75.0, "пентены",  485.0, 5),
            ("C6-ол",  "O",  75.0,  63.0, "гексены",  580.0, 6),
            ("C7-ол",  "O",  60.0,  50.0, "гептены",  675.0, 7),
            ("C8-ол",  "O",  50.0,  40.0, "октены",   770.0, 8),
            ("C9-ол",  "O",  40.0,  30.0, "нонены",   865.0, 9),
            ("C10-ол", "O",  30.0,  25.0, "децены",   960.0, 10),

            # ==========================================================
            # ⭕ НАФТЕНЫ
            # ==========================================================
            ("N-C5", "N", 101.0,  97.0, "C5-нафтены", 515.0, 5),
            ("N-C6", "N",  95.0,  88.0, "C6-нафтены", 620.0, 6),
            ("N-C7", "N",  80.0,  75.0, "C7-нафтены", 725.0, 7),
            ("N-C8", "N",  70.0,  65.0, "C8-нафтены", 825.0, 8),

            # ==========================================================
            # 🟣 АРОМАТИКА (тяжелая)
            # ==========================================================
            ("A-C9+", "A", 112.0, 102.0, "C9+ ароматика", 910.0, 9),

            # ==========================================================
            # 🧪 КИСЛОРОДСОДЕРЖАЩИЕ
            # ==========================================================
            ("МТБЭ",   "OXY", 118.0, 101.0, "метил-трет-бутиловый эфир", 730.0, 5),
            ("Этанол", "OXY", 109.0,  90.0, "этиловый спирт",            450.0, 2),
            ("ЭТБЭ",   "OXY", 118.0, 102.0, "этил-трет-бутиловый эфир",  820.0, 6),
        ]

        for name, cls, ron, mon, desc, lri, carbon in data:
            self.db[name] = ComponentProperties(cls, ron, mon, desc, lri, carbon)

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
            name = str(entry.get("group", "")).strip()
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
                "group": name, "class": props.class_name,
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

    # ==========================================================
    # 🔍 ПРОВЕРКА РАЗМЕТКИ ПО LRI
    # ==========================================================
    def calculate_lri(self, retention_time: float, t_n: float, t_n1: float, n_carbon: int) -> float:
        """
        Расчет линейного индекса удерживания (LRI).
        Формула Ван ден Дула и Кратца для режима программирования температуры.
        """
        if t_n1 <= t_n or retention_time < t_n:
            return 0.0
        lri = 100.0 * (n_carbon + (retention_time - t_n) / (t_n1 - t_n))
        return round(lri, 1)

    def check_peak_identification(self, chromatogram: List[Dict], tolerance: float = 5.0) -> Dict:
        """Проверка корректности идентификации пиков по LRI"""
        results = {"peaks": [], "warnings": [], "statistics": {}}

        # Собираем н-алканы для интерполяции
        n_alkanes = {}
        for entry in chromatogram:
            group = str(entry.get("group", "")).strip()
            rt = entry.get("retention_time")
            if rt is None or group not in self.db:
                continue
            try:
                rt = float(rt)
            except (ValueError, TypeError):
                continue
            if rt <= 0:
                continue
            props = self.db[group]
            # Опорные н-алканы: н-Пентан, н-Гексан, н-Гептан, н-Октан, н-Нонан, н-Декан, н-C4, н-Ундекан+
            if group.startswith("н-") and props.carbon_number:
                n_alkanes[props.carbon_number] = rt

        if len(n_alkanes) < 2:
            results["warnings"].append(
                "Недостаточно н-алканов для расчета LRI "
                "(нужно минимум 2, рекомендуется 4-6)"
            )
            return results

        sorted_carbons = sorted(n_alkanes.keys())

        # Проверяем каждый пик
        deviations = []
        for entry in chromatogram:
            group = str(entry.get("group", "")).strip()
            rt = entry.get("retention_time")
            try:
                content = float(entry.get("content", 0))
                rt = float(rt) if rt is not None else 0
            except (ValueError, TypeError):
                continue
            if rt <= 0 or content <= 0 or group not in self.db:
                continue

            props = self.db[group]
            if props.table_lri is None:
                continue

            calculated_lri = 0.0

            # Для н-алканов LRI строго = 100 × n
            if group.startswith("н-") and props.carbon_number:
                calculated_lri = props.carbon_number * 100.0
            else:
                # Ищем "скобки" из н-алканов
                t_n = None
                t_n1 = None
                n_carbon = 0
                for c in sorted_carbons:
                    if n_alkanes[c] <= rt:
                        t_n = n_alkanes[c]
                        n_carbon = c
                    elif n_alkanes[c] > rt and t_n1 is None:
                        t_n1 = n_alkanes[c]
                        break

                if t_n is not None and t_n1 is not None:
                    calculated_lri = self.calculate_lri(rt, t_n, t_n1, n_carbon)
                else:
                    results["warnings"].append(
                        f"{group}: tR={rt:.2f} мин вне диапазона н-алканов "
                        f"({min(n_alkanes.values()):.2f}-{max(n_alkanes.values()):.2f} мин)"
                    )
                    continue

            deviation = calculated_lri - props.table_lri
            deviations.append(deviation)
            status = "✅" if abs(deviation) <= tolerance else "❌"

            results["peaks"].append({
                "group": group,
                "class": props.class_name,
                "retention_time": round(rt, 3),
                "calculated_lri": round(calculated_lri, 1),
                "table_lri": props.table_lri,
                "deviation": round(deviation, 1),
                "status": status,
                "content": content,
            })

        if deviations:
            results["statistics"] = {
                "total_peaks": len(deviations),
                "correct": sum(1 for d in deviations if abs(d) <= tolerance),
                "incorrect": sum(1 for d in deviations if abs(d) > tolerance),
                "mean_deviation": round(sum(deviations) / len(deviations), 1),
                "max_deviation": round(max(abs(d) for d in deviations), 1),
            }

        return results

    # ==========================================================
    # ⚙️ КАЛИБРОВКА LRI
    # ==========================================================
    def update_table_lri(self, group: str, new_lri: float) -> bool:
        """Обновление табличного значения LRI"""
        if group in self.db:
            self.db[group].table_lri = new_lri
            return True
        return False

    def load_custom_lri_table(self, lri_data: List[Dict]) -> Dict:
        """Загрузка пользовательской таблицы LRI"""
        results = {"updated": [], "not_found": [], "errors": []}
        for entry in lri_data:
            group = str(entry.get("group", "")).strip()
            lri = entry.get("table_lri")
            if not group or lri is None:
                continue
            try:
                lri_value = float(lri)
                if self.update_table_lri(group, lri_value):
                    results["updated"].append(f"{group}: {lri_value}")
                else:
                    results["not_found"].append(group)
            except (ValueError, TypeError):
                results["errors"].append(f"{group}: некорректное значение '{lri}'")
        return results

    def get_lri_table(self) -> List[Dict]:
        """Получение текущей таблицы LRI"""
        table = []
        for name, props in self.db.items():
            if props.table_lri is not None:
                table.append({
                    "group": name,
                    "class": props.class_name,
                    "description": props.description,
                    "table_lri": props.table_lri,
                })
        return sorted(table, key=lambda x: x["table_lri"])

    def export_lri_table(self) -> str:
        """Экспорт таблицы LRI в CSV"""
        lines = ["group,table_lri,description"]
        for entry in self.get_lri_table():
            lines.append(f"{entry['group']},{entry['table_lri']},{entry['description']}")
        return "\n".join(lines)
