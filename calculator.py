"""
Модуль расчета октанового числа с автоидентификацией и диагностикой.
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


class OctaneCalculator:
    def __init__(self):
        self.db: Dict[str, ComponentProperties] = {}
        self._load_database()

    def _load_database(self):
        data = [
            # ОПОРНЫЕ Н-АЛКАНЫ (обязательны для калибровки)
            ("н-Пентан",     "P",   62.0,  62.0, "н-пентан",                500.0, 5),
            ("н-Гексан",     "P",   25.0,  26.0, "н-гексан",                600.0, 6),
            ("н-Гептан",     "P",    0.0,   0.0, "н-гептан",                700.0, 7),
            ("н-Октан",      "P",  -10.0, -17.0, "н-октан",                 800.0, 8),
            ("н-Нонан",      "P",  -20.0, -30.0, "н-нонан",                 900.0, 9),
            ("н-Декан",      "P",  -30.0, -40.0, "н-декан",                1000.0, 10),

            # ДРУГИЕ ОПОРНЫЕ ПИКИ
            ("Изопентан",    "I",   92.0,  90.0, "изопентан",               475.0, 5),
            ("Бензол",       "A",   99.0,  91.0, "бензол",                  650.0, 6),
            ("Толуол",       "A",  120.0, 109.0, "толуол",                  760.0, 7),
            ("Изооктан",     "I",  100.0, 100.0, "2,2,4-ТМП",               750.0, 8),
            ("Этилбензол",   "A",   98.0, 104.0, "этилбензол",              850.0, 8),
            ("п-Ксилол",     "A",  116.0, 103.0, "п-ксилол",                865.0, 8),
            ("м-Ксилол",     "A",  117.0, 104.0, "м-ксилол",                870.0, 8),
            ("м-/п-Ксилол",  "A",  117.0, 104.0, "м- + п-ксилол",           868.0, 8),
            ("о-Ксилол",     "A",  117.0, 102.0, "о-ксилол",                885.0, 8),

            # ГРУППОВЫЕ
            ("н-C4",   "P",   94.0,  91.0, "н-бутан",                   400.0, 4),
            ("i-C4",   "I",  102.0,  97.0, "изобутан",                  385.0, 4),
            ("i-C6",   "I",   85.0,  80.0, "C6-изомеры",                560.0, 6),
            ("i-C7",   "I",   75.0,  70.0, "C7-изомеры",                650.0, 7),
            ("i-C8",   "I",   70.0,  70.0, "C8-изомеры",                740.0, 8),
            ("i-C9",   "I",   65.0,  60.0, "C9-изомеры",                830.0, 9),
            ("i-C10",  "I",   55.0,  50.0, "C10-изомеры",               920.0, 10),

            # ИЗОМЕРЫ ОКТАНА
            ("2-MeC7",          "I",  56.0,  56.0, "2-метилгептан",           735.0, 8),
            ("3-MeC7",          "I",  65.0,  62.0, "3-метилгептан",           745.0, 8),
            ("4-MeC7",          "I",  68.0,  65.0, "4-метилгептан",           750.0, 8),
            ("2,2-diMeC6",      "I",  80.0,  75.0, "2,2-диметилгексан",       720.0, 8),
            ("2,3-diMeC6",      "I",  78.0,  73.0, "2,3-диметилгексан",       730.0, 8),
            ("2,4-diMeC6",      "I",  82.0,  78.0, "2,4-диметилгексан",       735.0, 8),
            ("2,5-diMeC6",      "I",  85.0,  80.0, "2,5-диметилгексан",       740.0, 8),
            ("3,3-diMeC6",      "I",  75.0,  70.0, "3,3-диметилгексан",       725.0, 8),
            ("3,4-diMeC6",      "I",  76.0,  72.0, "3,4-диметилгексан",       738.0, 8),
            ("2,2,4-triMeC5",   "I", 100.0, 100.0, "2,2,4-триметилпентан",    750.0, 8),
            ("2,3,4-triMeC5",   "I",  88.0,  83.0, "2,3,4-триметилпентан",    752.0, 8),

            # ИЗОМЕРЫ НОНАНА
            ("2-MeC8",        "I",  45.0,  45.0, "2-метилоктан",         830.0, 9),
            ("3-MeC8",        "I",  55.0,  52.0, "3-метилоктан",         840.0, 9),
            ("4-MeC8",        "I",  60.0,  57.0, "4-метилоктан",         845.0, 9),
            ("2,2-diMeC7",    "I",  70.0,  65.0, "2,2-диметилгептан",    815.0, 9),
            ("2,3-diMeC7",    "I",  72.0,  68.0, "2,3-диметилгептан",    825.0, 9),
            ("2,4-diMeC7",    "I",  75.0,  70.0, "2,4-диметилгептан",    830.0, 9),
            ("2,5-diMeC7",    "I",  78.0,  73.0, "2,5-диметилгептан",    835.0, 9),

            # ИЗОМЕРЫ ДЕКАНА
            ("2-MeC9",        "I",  38.0,  38.0, "2-метилнонан",         920.0, 10),
            ("3-MeC9",        "I",  48.0,  45.0, "3-метилнонан",         930.0, 10),
            ("4-MeC9",        "I",  52.0,  49.0, "4-метилнонан",         935.0, 10),
            ("2,2-diMeC8",    "I",  65.0,  60.0, "2,2-диметилоктан",     915.0, 10),
            ("2,3-diMeC8",    "I",  68.0,  63.0, "2,3-диметилоктан",     925.0, 10),
            ("2,4-diMeC8",    "I",  70.0,  65.0, "2,4-диметилоктан",     930.0, 10),

            # ОЛЕФИНЫ
            ("C4-ол",  "O",  95.0,  80.0, "бутены",   390.0, 4),
            ("C5-ол",  "O",  90.0,  75.0, "пентены",  485.0, 5),
            ("C6-ол",  "O",  75.0,  63.0, "гексены",  580.0, 6),
            ("C7-ол",  "O",  60.0,  50.0, "гептены",  675.0, 7),
            ("C8-ол",  "O",  50.0,  40.0, "октены",   770.0, 8),

            # НАФТЕНЫ
            ("N-C5", "N", 101.0,  97.0, "C5-нафтены", 515.0, 5),
            ("N-C6", "N",  95.0,  88.0, "C6-нафтены", 620.0, 6),
            ("N-C7", "N",  80.0,  75.0, "C7-нафтены", 725.0, 7),
            ("N-C8", "N",  70.0,  65.0, "C8-нафтены", 825.0, 8),

            # АРОМАТИКА
            ("A-C9+", "A", 112.0, 102.0, "C9+ ароматика", 910.0, 9),

            # КИСЛОРОДСОДЕРЖАЩИЕ
            ("МТБЭ",   "OXY", 118.0, 101.0, "МТБЭ", 730.0, 5),
            ("Этанол", "OXY", 109.0,  90.0, "этанол", 450.0, 2),
            ("ЭТБЭ",   "OXY", 118.0, 102.0, "ЭТБЭ", 820.0, 6),
        ]
        for name, cls, ron, mon, desc, lri, carbon in data:
            self.db[name] = ComponentProperties(cls, ron, mon, desc, lri, carbon)

    def calculate_lri(self, retention_time: float, t_n: float, t_n1: float, n_carbon: int) -> float:
        if t_n1 <= t_n or retention_time < t_n:
            return 0.0
        return 100.0 * (n_carbon + (retention_time - t_n) / (t_n1 - t_n))

    def get_n_alkanes(self, peaks: List[Dict]) -> Dict[int, float]:
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
        """
        Идентификация всех пиков.
        Возвращает (обновлённые пики, список диагностик).
        """
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

            # Пропускаем, если имя уже есть и overwrite=False
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

    def calculate(self, chromatogram: List[Dict], normalize: bool = True) -> Dict:
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
