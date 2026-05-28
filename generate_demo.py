"""
generate_demo.py — 不動産買取再販ダッシュボード PoC のデモデータ生成

設計方針:
  - スター型データモデルに準拠（table_spec.xlsx）
  - 2支店分のみ生成（PoC実行時間短縮のため）
  - 設計は22支店スケール可能（BRANCH_COUNT パラメータで調整）
  - 17期実績の比率に寄せる（指示書8章）
  - スナップショット列（契約時点支店ID等）を正しく埋める
  - 1案件→0〜2契約の関係を正しく反映

出力:
  data/dim_社員.csv
  data/dim_支店.csv
  data/dim_情報源.csv
  data/dim_出口.csv
  data/dim_カレンダー.csv
  data/dim_物件.csv
  data/fact_案件.csv
  data/fact_契約.csv

使い方:
  python generate_demo.py
"""

import os
import random
import csv
from datetime import date, datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional
import numpy as np

# ============================================================
# 設定
# ============================================================
random.seed(42)
np.random.seed(42)

# PoC用: 2支店のみ
BRANCH_COUNT = 2
EMPLOYEES_PER_BRANCH = 5   # 1支店あたり営業5名 + 事務2名
OFFICE_PER_BRANCH = 2

# 期間: 24か月
START_DATE = date(2024, 4, 1)
END_DATE = date(2026, 3, 31)

# 17期実績比率（指示書8章）。全社=22支店なので、2支店分にスケールダウン
# 月次契約数: 売却40-52 / 仲介61-85 / 仕入62-81 (全社)
# 2支店分: 売却4-5 / 仲介6-8 / 仕入6-8
MONTHLY_BAITORI_RANGE = (6, 8)     # 仕入（買取契約）
MONTHLY_CHUKAI_RANGE = (6, 8)      # 仲介契約
MONTHLY_BAIKYAKU_RANGE = (4, 5)    # 売却契約（買取再販の売却）

# 月次粗利目安: 全社1.7〜2.0億/月 → 2支店分で約1500-1800万/月
TARGET_MONTHLY_GP_RANGE = (15_000_000, 18_000_000)

OUTPUT_DIR = "data"


# ============================================================
# データクラス
# ============================================================
@dataclass
class Branch:
    branch_id: int
    branch_name: str
    area: str
    opened_year_month: date
    rank: str
    branch_type: str
    is_self: bool


@dataclass
class Employee:
    employee_id: int
    employee_name: str
    current_branch_id: int
    hire_year_month: date
    previous_industry: str
    current_employment_type: str
    role_type: str
    is_retired: bool
    retire_year_month: Optional[date]
    # 異動履歴（PoCでは簡易化、現状のみ保持）
    branch_history: list = field(default_factory=list)  # [(start_date, branch_id), ...]


# ============================================================
# ヘルパー
# ============================================================
def daterange_months(start: date, end: date):
    """月初日のシーケンス"""
    cur = date(start.year, start.month, 1)
    while cur <= end:
        yield cur
        if cur.month == 12:
            cur = date(cur.year + 1, 1, 1)
        else:
            cur = date(cur.year, cur.month + 1, 1)


def daterange_days(start: date, end: date):
    cur = start
    while cur <= end:
        yield cur
        cur += timedelta(days=1)


def random_business_day_in_month(year_month: date) -> date:
    """指定月内のランダムな営業日（土日を簡易除外）"""
    if year_month.month == 12:
        next_month = date(year_month.year + 1, 1, 1)
    else:
        next_month = date(year_month.year, year_month.month + 1, 1)
    last_day = (next_month - timedelta(days=1)).day
    while True:
        day = random.randint(1, last_day)
        d = date(year_month.year, year_month.month, day)
        if d.weekday() < 5:
            return d


# ============================================================
# 1. dim_支店
# ============================================================
def build_branches() -> list[Branch]:
    candidates = [
        Branch(1, "横浜支店", "首都圏", date(2018, 4, 1), "A", "新規出店", True),
        Branch(2, "渋谷支店", "首都圏", date(2020, 10, 1), "B", "新規出店", False),
    ]
    return candidates[:BRANCH_COUNT]


# ============================================================
# 2. dim_社員
# ============================================================
JAPANESE_FAMILY = ["山田", "佐藤", "鈴木", "高橋", "田中", "伊藤", "渡辺", "中村", "小林", "加藤",
                   "吉田", "山口", "松本", "井上", "木村", "林", "斎藤", "清水", "山崎", "森"]
JAPANESE_GIVEN = ["太郎", "次郎", "三郎", "健", "誠", "拓也", "翔", "大輔", "和也", "智也",
                  "花子", "美咲", "彩", "麻衣", "由美", "智子", "恵子", "陽子", "真理", "明子"]
PREVIOUS_INDUSTRIES = ["大手仲介", "買取仕入経験", "注文住宅", "未経験", "新卒"]
PREVIOUS_INDUSTRY_WEIGHTS = [0.30, 0.25, 0.15, 0.20, 0.10]

EMPLOYMENT_TYPES_SALES = ["正社員", "派遣", "クルー"]
EMPLOYMENT_WEIGHTS_SALES = [0.75, 0.15, 0.10]


def build_employees(branches: list[Branch]) -> list[Employee]:
    employees: list[Employee] = []
    employee_id = 1001
    for b in branches:
        # 営業
        for _ in range(EMPLOYEES_PER_BRANCH):
            full_name = f"{random.choice(JAPANESE_FAMILY)} {random.choice(JAPANESE_GIVEN)}"
            prev = np.random.choice(PREVIOUS_INDUSTRIES, p=PREVIOUS_INDUSTRY_WEIGHTS)
            emp_type = np.random.choice(EMPLOYMENT_TYPES_SALES, p=EMPLOYMENT_WEIGHTS_SALES)
            # 入社月: 過去5年で分散、新卒は4月集中
            if prev == "新卒":
                year = random.choice([2020, 2021, 2022, 2023, 2024])
                hire = date(year, 4, 1)
            else:
                year = random.choice([2019, 2020, 2021, 2022, 2023, 2024])
                month = random.randint(1, 12)
                hire = date(year, month, 1)
            employees.append(Employee(
                employee_id=employee_id,
                employee_name=full_name,
                current_branch_id=b.branch_id,
                hire_year_month=hire,
                previous_industry=str(prev),
                current_employment_type=str(emp_type),
                role_type="営業",
                is_retired=False,
                retire_year_month=None,
                branch_history=[(hire, b.branch_id)],
            ))
            employee_id += 1
        # 事務
        for _ in range(OFFICE_PER_BRANCH):
            full_name = f"{random.choice(JAPANESE_FAMILY)} {random.choice(JAPANESE_GIVEN)}"
            year = random.choice([2018, 2019, 2020, 2021, 2022])
            month = random.randint(1, 12)
            hire = date(year, month, 1)
            employees.append(Employee(
                employee_id=employee_id,
                employee_name=full_name,
                current_branch_id=b.branch_id,
                hire_year_month=hire,
                previous_industry="未経験",
                current_employment_type="正社員",
                role_type="事務",
                is_retired=False,
                retire_year_month=None,
                branch_history=[(hire, b.branch_id)],
            ))
            employee_id += 1
    return employees


# ============================================================
# 3. dim_情報源
# ============================================================
INFO_SOURCES = [
    (1, "飛び込み", "プッシュ型", 1.2),
    (2, "紹介", "ネットワーク型", 0.7),
    (3, "レインズ", "プル型", 1.0),
    (4, "HP", "プル型", 0.9),
    (5, "SNS", "プル型", 1.1),
    (6, "業者紹介", "ネットワーク型", 0.8),
]
# 営業ごとの情報源偏り重み（情報源数=6）
INFO_SOURCE_BIAS_PATTERNS = [
    [0.40, 0.20, 0.10, 0.10, 0.05, 0.15],   # 飛び込み偏重
    [0.10, 0.45, 0.15, 0.10, 0.05, 0.15],   # 紹介偏重
    [0.15, 0.15, 0.30, 0.20, 0.10, 0.10],   # レインズ偏重
    [0.10, 0.15, 0.15, 0.35, 0.15, 0.10],   # HP偏重
    [0.20, 0.20, 0.15, 0.15, 0.20, 0.10],   # バランス型
]


# ============================================================
# 4. dim_出口
# ============================================================
EXITS = [
    (1, "エンド販売", "個人", "現況"),
    (2, "エンド販売", "個人", "再販"),
    (3, "エンド販売", "法人", "現況"),
    (4, "エンド販売", "法人", "再販"),
    (5, "業者販売", "法人", "現況"),
    (6, "業者販売", "法人", "再販"),
    (7, "再販前提", "法人", "現況"),
    (8, "仲介出口", "個人", "現況"),   # 仲介契約用
]


# ============================================================
# 5. dim_カレンダー
# ============================================================
def build_calendar(start: date, end: date) -> list[dict]:
    """会計期は4月開始で仮置き"""
    rows = []
    for d in daterange_days(start - timedelta(days=90), end + timedelta(days=90)):
        # 期: 2024/4〜2025/3 が18期、2025/4〜2026/3 が19期 と仮置き
        if d.month >= 4:
            fiscal_period = d.year - 2006   # 2024年4月 → 18期
        else:
            fiscal_period = d.year - 2007   # 2024年1月〜3月 → 17期
        # 上期: 4-9月, 下期: 10-3月
        half = "H1" if 4 <= d.month <= 9 else "H2"
        rows.append({
            "日付": d.isoformat(),
            "期": fiscal_period,
            "上期下期": half,
            "年月": d.strftime("%Y-%m"),
            "月": d.month,
            "週": d.isocalendar()[1],
            "曜日": d.weekday(),
            "営業日フラグ": d.weekday() < 5,
        })
    return rows


# ============================================================
# 6. 案件・契約・物件の生成
# ============================================================
@dataclass
class Anken:
    案件ID: str
    登録日: date
    情報源ID: int
    登録担当社員ID: int
    登録時点支店ID: int
    案件種別: str          # 売却仲介 / 買取 / 購入仲介
    成約フラグ: bool
    粗利_見込み: int
    ステータス: str
    失注理由: Optional[str]


@dataclass
class Keiyaku:
    契約ID: str
    案件ID: str
    契約日: date
    決済日: Optional[date]
    契約担当社員ID: int
    契約時点支店ID: int
    契約時点雇用形態: str
    契約種別: str           # 買取 / 仲介 / 売却
    出口ID: Optional[int]
    物件ID: Optional[str]
    粗利_確定: int
    投下現金額: Optional[int]
    サンタメフラグ: bool


@dataclass
class Bukken:
    物件ID: str
    エリア: str
    種別: str
    取得日: date
    取得価格: int
    取得支店ID: int
    売却契約日: Optional[date]
    売却日: Optional[date]
    売却価格: Optional[int]


PROPERTY_TYPES = ["戸建", "マンション", "土地"]
PROPERTY_TYPE_WEIGHTS = [0.45, 0.40, 0.15]
AREAS_BY_BRANCH = {
    1: ["横浜市西区", "横浜市中区", "横浜市神奈川区", "横浜市磯子区"],
    2: ["渋谷区", "目黒区", "世田谷区", "港区"],
}


def generate_anken_and_keiyaku(
    branches: list[Branch],
    employees: list[Employee],
) -> tuple[list[Anken], list[Keiyaku], list[Bukken]]:
    ankens: list[Anken] = []
    keiyakus: list[Keiyaku] = []
    bukkens: list[Bukken] = []

    anken_seq = 1
    keiyaku_seq = 1
    bukken_seq = 1

    sales_employees = [e for e in employees if e.role_type == "営業"]
    # 営業ごとに情報源偏りを固定
    employee_info_bias = {
        e.employee_id: random.choice(INFO_SOURCE_BIAS_PATTERNS)
        for e in sales_employees
    }

    for month_start in daterange_months(START_DATE, END_DATE):
        # その月に在籍中の営業
        active_sales = [
            e for e in sales_employees
            if e.hire_year_month <= month_start
            and (not e.is_retired or (e.retire_year_month and e.retire_year_month > month_start))
        ]
        if not active_sales:
            continue

        # 月次契約数（17期比率に従う）
        n_baitori = random.randint(*MONTHLY_BAITORI_RANGE)
        n_chukai = random.randint(*MONTHLY_CHUKAI_RANGE)
        n_baikyaku = random.randint(*MONTHLY_BAIKYAKU_RANGE)

        # 月次の案件登録は、契約に至る分 + 失注分を生成
        # 仮: 成約率 35-50% → 登録案件数 = (n_baitori + n_chukai) / 0.4 程度
        # n_baikyaku は買取再販の売却なので、過去の買取案件から発生（新規案件としては数えない）
        target_seiyaku = n_baitori + n_chukai
        n_anken_this_month = int(target_seiyaku / random.uniform(0.35, 0.50))

        for _ in range(n_anken_this_month):
            emp = random.choice(active_sales)
            登録日 = random_business_day_in_month(month_start)
            # 情報源偏り
            info_idx = np.random.choice(6, p=employee_info_bias[emp.employee_id])
            情報源ID = INFO_SOURCES[info_idx][0]
            # 案件種別はランダムだが、買取と仲介の比率を考慮
            anken_type = random.choices(
                ["買取", "売却仲介", "購入仲介"],
                weights=[0.55, 0.30, 0.15],
            )[0]
            # 粗利見込みは案件種別と情報源によって分布
            if anken_type == "買取":
                gp_estimate = int(np.random.lognormal(np.log(2_000_000), 0.4))
            else:
                gp_estimate = int(np.random.lognormal(np.log(800_000), 0.4))
            # 成約判定（情報源依存）
            base_close_rate = {
                1: 0.30,  # 飛び込み
                2: 0.55,  # 紹介（高効率）
                3: 0.45,  # レインズ
                4: 0.40,  # HP
                5: 0.35,  # SNS
                6: 0.50,  # 業者紹介
            }[情報源ID]
            # 出身業種補正
            industry_boost = {
                "大手仲介": 0.05,
                "買取仕入経験": 0.08,
                "注文住宅": 0.02,
                "未経験": -0.05,
                "新卒": -0.08,
            }[emp.previous_industry]
            close_rate = max(0.10, min(0.85, base_close_rate + industry_boost))
            成約 = random.random() < close_rate

            ステータス = "成約" if 成約 else random.choice(["失注", "失注", "活動中", "保留"])
            失注理由 = None
            if ステータス == "失注":
                失注理由 = random.choice(["価格不一致", "競合負け", "オーナー都合", "条件不一致"])

            anken_id = f"AK{月_to_yymm(登録日)}{anken_seq:04d}"
            anken_seq += 1

            anken = Anken(
                案件ID=anken_id,
                登録日=登録日,
                情報源ID=情報源ID,
                登録担当社員ID=emp.employee_id,
                登録時点支店ID=emp.current_branch_id,   # スナップショット
                案件種別=anken_type,
                成約フラグ=(ステータス == "成約"),
                粗利_見込み=gp_estimate,
                ステータス=ステータス,
                失注理由=失注理由,
            )
            ankens.append(anken)

            # 成約案件には契約を生成
            if anken.成約フラグ:
                契約日 = 登録日 + timedelta(days=random.randint(15, 90))
                if anken_type == "買取":
                    # 買取契約を生成
                    決済日 = 契約日 + timedelta(days=random.randint(20, 45))
                    取得価格 = int(np.random.lognormal(np.log(15_000_000), 0.45))  # 中心1500万に下げ
                    # 物件作成
                    bukken_id = f"PR{月_to_yymm(決済日)}{bukken_seq:04d}"
                    bukken_seq += 1
                    bukken = Bukken(
                        物件ID=bukken_id,
                        エリア=random.choice(AREAS_BY_BRANCH[emp.current_branch_id]),
                        種別=str(np.random.choice(PROPERTY_TYPES, p=PROPERTY_TYPE_WEIGHTS)),
                        取得日=決済日,
                        取得価格=取得価格,
                        取得支店ID=emp.current_branch_id,
                        売却契約日=None,
                        売却日=None,
                        売却価格=None,
                    )
                    bukkens.append(bukken)
                    # 買取契約レコード
                    契約ID = f"CT{月_to_yymm(契約日)}{keiyaku_seq:04d}"
                    keiyaku_seq += 1
                    keiyakus.append(Keiyaku(
                        契約ID=契約ID,
                        案件ID=anken_id,
                        契約日=契約日,
                        決済日=決済日,
                        契約担当社員ID=emp.employee_id,
                        契約時点支店ID=emp.current_branch_id,
                        契約時点雇用形態=emp.current_employment_type,
                        契約種別="買取",
                        出口ID=None,
                        物件ID=bukken_id,
                        粗利_確定=0,   # 買取時点では粗利確定なし
                        投下現金額=取得価格,
                        サンタメフラグ=False,   # 売却時に判定
                    ))
                    # 後で売却契約をスケジュール（在庫日数の対数正規分布）
                    在庫日数 = max(10, int(np.random.lognormal(np.log(60), 0.6)))
                    売却契約予定日 = 決済日 + timedelta(days=在庫日数)
                    売却決済予定日 = 売却契約予定日 + timedelta(days=random.randint(20, 45))
                    if 売却決済予定日 <= END_DATE:
                        # 売却契約・売却決済を生成
                        粗利_倍率 = np.random.uniform(0.06, 0.15)   # 取得価格の6-15%が粗利
                        粗利 = int(取得価格 * 粗利_倍率)
                        売却価格 = 取得価格 + 粗利
                        # サンタメ判定: 30%の確率でTRUE（要ヒアリング）
                        サンタメ = random.random() < 0.20
                        # 出口ID
                        出口ID = random.choice([1, 2, 3, 4])
                        if サンタメ:
                            出口ID = random.choice([5, 6, 7])
                        契約ID = f"CT{月_to_yymm(売却契約予定日)}{keiyaku_seq:04d}"
                        keiyaku_seq += 1
                        keiyakus.append(Keiyaku(
                            契約ID=契約ID,
                            案件ID=anken_id,
                            契約日=売却契約予定日,
                            決済日=売却決済予定日,
                            契約担当社員ID=emp.employee_id,
                            契約時点支店ID=emp.current_branch_id,
                            契約時点雇用形態=emp.current_employment_type,
                            契約種別="売却",
                            出口ID=出口ID,
                            物件ID=bukken_id,
                            粗利_確定=粗利,
                            投下現金額=None,
                            サンタメフラグ=サンタメ,
                        ))
                        # 物件の売却情報更新
                        bukken.売却契約日 = 売却契約予定日
                        bukken.売却日 = 売却決済予定日
                        bukken.売却価格 = 売却価格
                elif anken_type in ("売却仲介", "購入仲介"):
                    # 仲介契約
                    粗利 = int(np.random.lognormal(np.log(500_000), 0.4))  # 中心50万に
                    契約ID = f"CT{月_to_yymm(契約日)}{keiyaku_seq:04d}"
                    keiyaku_seq += 1
                    keiyakus.append(Keiyaku(
                        契約ID=契約ID,
                        案件ID=anken_id,
                        契約日=契約日,
                        決済日=契約日 + timedelta(days=random.randint(20, 45)),
                        契約担当社員ID=emp.employee_id,
                        契約時点支店ID=emp.current_branch_id,
                        契約時点雇用形態=emp.current_employment_type,
                        契約種別="仲介",
                        出口ID=8,
                        物件ID=None,
                        粗利_確定=粗利,
                        投下現金額=None,
                        サンタメフラグ=False,
                    ))

    return ankens, keiyakus, bukkens


def 月_to_yymm(d: date) -> str:
    return d.strftime("%y%m")


# ============================================================
# CSV出力
# ============================================================
def write_csv(path: str, rows: list[dict], fieldnames: list[str]):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 1. dim_支店
    branches = build_branches()
    write_csv(
        f"{OUTPUT_DIR}/dim_支店.csv",
        [{
            "支店ID": b.branch_id, "支店名": b.branch_name, "エリア": b.area,
            "開設年月": b.opened_year_month.isoformat(), "ランク": b.rank,
            "出店種別": b.branch_type, "自支店フラグ": b.is_self,
        } for b in branches],
        ["支店ID", "支店名", "エリア", "開設年月", "ランク", "出店種別", "自支店フラグ"],
    )
    print(f"dim_支店: {len(branches)} 行")

    # 2. dim_社員
    employees = build_employees(branches)
    write_csv(
        f"{OUTPUT_DIR}/dim_社員.csv",
        [{
            "社員ID": e.employee_id, "氏名": e.employee_name,
            "現在支店ID": e.current_branch_id,
            "入社年月": e.hire_year_month.isoformat(),
            "出身業種": e.previous_industry,
            "現在雇用形態": e.current_employment_type,
            "職種": e.role_type, "退職フラグ": e.is_retired,
            "退職年月": e.retire_year_month.isoformat() if e.retire_year_month else "",
        } for e in employees],
        ["社員ID", "氏名", "現在支店ID", "入社年月", "出身業種",
         "現在雇用形態", "職種", "退職フラグ", "退職年月"],
    )
    print(f"dim_社員: {len(employees)} 行")

    # 3. dim_情報源
    write_csv(
        f"{OUTPUT_DIR}/dim_情報源.csv",
        [{
            "情報源ID": r[0], "情報源名": r[1], "カテゴリ": r[2], "コスト係数": r[3],
        } for r in INFO_SOURCES],
        ["情報源ID", "情報源名", "カテゴリ", "コスト係数"],
    )
    print(f"dim_情報源: {len(INFO_SOURCES)} 行")

    # 4. dim_出口
    write_csv(
        f"{OUTPUT_DIR}/dim_出口.csv",
        [{
            "出口ID": r[0], "出口種別": r[1], "法人個人区分": r[2], "現況再販区分": r[3],
        } for r in EXITS],
        ["出口ID", "出口種別", "法人個人区分", "現況再販区分"],
    )
    print(f"dim_出口: {len(EXITS)} 行")

    # 5. dim_カレンダー
    calendar_rows = build_calendar(START_DATE, END_DATE)
    write_csv(
        f"{OUTPUT_DIR}/dim_カレンダー.csv",
        calendar_rows,
        ["日付", "期", "上期下期", "年月", "月", "週", "曜日", "営業日フラグ"],
    )
    print(f"dim_カレンダー: {len(calendar_rows)} 行")

    # 6. 案件・契約・物件
    ankens, keiyakus, bukkens = generate_anken_and_keiyaku(branches, employees)
    write_csv(
        f"{OUTPUT_DIR}/fact_案件.csv",
        [{
            "案件ID": a.案件ID, "登録日": a.登録日.isoformat(),
            "情報源ID": a.情報源ID, "登録担当社員ID": a.登録担当社員ID,
            "登録時点支店ID": a.登録時点支店ID, "案件種別": a.案件種別,
            "成約フラグ": a.成約フラグ, "粗利_見込み": a.粗利_見込み,
            "ステータス": a.ステータス,
            "失注理由": a.失注理由 if a.失注理由 else "",
        } for a in ankens],
        ["案件ID", "登録日", "情報源ID", "登録担当社員ID", "登録時点支店ID",
         "案件種別", "成約フラグ", "粗利_見込み", "ステータス", "失注理由"],
    )
    print(f"fact_案件: {len(ankens)} 行")

    write_csv(
        f"{OUTPUT_DIR}/fact_契約.csv",
        [{
            "契約ID": k.契約ID, "案件ID": k.案件ID,
            "契約日": k.契約日.isoformat(),
            "決済日": k.決済日.isoformat() if k.決済日 else "",
            "契約担当社員ID": k.契約担当社員ID,
            "契約時点支店ID": k.契約時点支店ID,
            "契約時点雇用形態": k.契約時点雇用形態,
            "契約種別": k.契約種別,
            "出口ID": k.出口ID if k.出口ID else "",
            "物件ID": k.物件ID if k.物件ID else "",
            "粗利_確定": k.粗利_確定,
            "投下現金額": k.投下現金額 if k.投下現金額 else "",
            "サンタメフラグ": k.サンタメフラグ,
        } for k in keiyakus],
        ["契約ID", "案件ID", "契約日", "決済日", "契約担当社員ID",
         "契約時点支店ID", "契約時点雇用形態", "契約種別",
         "出口ID", "物件ID", "粗利_確定", "投下現金額", "サンタメフラグ"],
    )
    print(f"fact_契約: {len(keiyakus)} 行")

    write_csv(
        f"{OUTPUT_DIR}/dim_物件.csv",
        [{
            "物件ID": b.物件ID, "エリア": b.エリア, "種別": b.種別,
            "取得日": b.取得日.isoformat(), "取得価格": b.取得価格,
            "取得支店ID": b.取得支店ID,
            "売却契約日": b.売却契約日.isoformat() if b.売却契約日 else "",
            "売却日": b.売却日.isoformat() if b.売却日 else "",
            "売却価格": b.売却価格 if b.売却価格 else "",
        } for b in bukkens],
        ["物件ID", "エリア", "種別", "取得日", "取得価格", "取得支店ID",
         "売却契約日", "売却日", "売却価格"],
    )
    print(f"dim_物件: {len(bukkens)} 行")

    # ===== 検証 =====
    print("\n===== 検証サマリ =====")
    # 月次粗利
    from collections import defaultdict
    monthly_gp = defaultdict(int)
    monthly_count_by_type = defaultdict(lambda: defaultdict(int))
    for k in keiyakus:
        ym = k.契約日.strftime("%Y-%m")
        monthly_gp[ym] += k.粗利_確定
        monthly_count_by_type[ym][k.契約種別] += 1

    sample_months = sorted(monthly_gp.keys())[:5]
    for ym in sample_months:
        types = monthly_count_by_type[ym]
        print(f"  {ym}: 粗利={monthly_gp[ym]:>12,}円  "
              f"買取={types.get('買取',0):>2}  "
              f"仲介={types.get('仲介',0):>2}  "
              f"売却={types.get('売却',0):>2}")

    n_baikyaku_total = sum(1 for k in keiyakus if k.契約種別 == "売却")
    n_santame = sum(1 for k in keiyakus if k.サンタメフラグ)
    print(f"\n  売却契約合計: {n_baikyaku_total}  (うちサンタメ: {n_santame}, {n_santame/n_baikyaku_total*100:.1f}%)")
    print(f"  在庫日数中央値: {np.median([(b.売却日 - b.取得日).days for b in bukkens if b.売却日]):.0f} 日")
    print(f"  成約率: {sum(1 for a in ankens if a.成約フラグ)/len(ankens)*100:.1f}%")


if __name__ == "__main__":
    main()
