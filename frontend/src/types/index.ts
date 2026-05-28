export interface Branch {
  支店ID: number
  支店名: string
  開設年月: string
}

export interface Alert {
  level: 'warning' | 'critical'
  message: string
}

export interface HealthKPIs {
  monthly_gp: number
  monthly_gp_delta_pct: number
  contract_count: number
  contract_count_delta: number
  closing_rate: number
  gp_per_person: number
}

export interface HealthData {
  kpis: HealthKPIs
  alerts: Alert[]
}

export interface MemberRow {
  社員ID: number
  氏名: string
  入社年月: string
  経過月数: number
  雇用形態: string
  出身業種: string
  契約件数: number
  粗利_確定: number
  粗利_前年: number
  成約率: number
}

export interface MemberData {
  members: MemberRow[]
  cohort_trend: { 年月: string; 入社年: string; 粗利_確定: number }[]
  thresholds: { gpp_warn: number; cr_warn: number }
  alerts: Alert[]
}

export interface InfoSourceData {
  src_count: { 情報源名: string; 月間平均案件数: number }[]
  portfolio: { 情報源名: string; '依存度(%)': number }[]
  src_stats: { 情報源名: string; 案件数: number; 成約数: number; 平均粗利: number; '成約率(%)': number }[]
  tenure_src: { 経験年次: string; 情報源名: string; 案件数: number }[]
  leadtime: { 情報源名: string; 平均日数: number; 中央値: number }[]
  roi: { 情報源名: string; ROI: number }[]
  thresholds: { dep_warn: number; cr_avg: number; cr_warn_src: number; gp_avg: number; roi_avg: number }
  alerts: Alert[]
}

export interface ExitData {
  pie_self: { 法人個人区分: string; 件数: number }[]
  pie_ly: { 法人個人区分: string; 件数: number }[]
  pie_all: { 法人個人区分: string; 件数: number }[]
  trend: { 年月: string; 現況再販区分: string; 件数: number }[]
  gp_by_branch: { 支店名: string; 平均粗利: number; is_self: boolean }[]
  avg_days: number | null
  med_days: number | null
  days_hist: { 在庫日数: number; 支店: string }[]
  thresholds: { inv_warn: number; inv_crit: number; dev_warn: number; dev_warn2: number }
  alerts: Alert[]
}

export interface ContractData {
  type_ratio_self: { 種別: string; 割合: number }[]
  type_ratio_all: { 種別: string; 割合: number }[]
  type_trend: { 年月: string; 契約種別: string; 件数: number }[]
  santame_pct: number
  cnt_trend: { 年月: string; 契約種別: string; 件数: number }[]
  branch_stats: { 支店名: string; '1人当たり粗利': number; '1人当たり契約数': number; is_self: boolean }[]
  inv_hist: { 在庫日数: number }[]
  inv_stats: { med: number; avg: number }
  turnover_rate: number
  cim: { avg: number | null; med: number | null }
  lead_time_hist: { リードタイム: number }[]
  lead_time_stats: { avg: number | null; med: number | null }
  by_type: { 種別: string; 平均在庫日数: number; 中央値在庫日数: number; 平均粗利率: number; 件数: number }[]
  by_type_area: { 種別: string; エリア: string; 平均在庫日数: number; 平均粗利率: number; 件数: number }[]
  long_inv: { long_val: number; total_val: number; long_pct: number }
  thresholds: { gpp_warn: number; st_lo: number; st_hi: number; inv_warn: number; inv_crit: number; cim_warn: number }
  alerts: Alert[]
}

export interface GrowthData {
  branch_phases: { 支店名: string; phase: string; elapsed_mo: number; is_self: boolean }[]
  branch_gp_trend: { 支店名: string; 年月: string; 月次粗利: number; is_self: boolean }[]
  avg_by_month: { 年月: string; 月次粗利: number }[]
  cohort: { 入社期: string; 経過月数: number; 粗利_確定: number }[]
  industry: { 出身業種: string; 経過月数: number; 粗利_確定: number }[]
  tenure_src: { 経験年次: string; 情報源名: string; 案件数: number; '割合(%)': number }[]
  thresholds: { gpp_warn: number; dep_warn: number }
  alerts: Alert[]
}

export interface MetaData {
  branches: Branch[]
  months: string[]
  info_sources: string[]
  industries: string[]
  areas: string[]
  prop_types: string[]
  exit_types: string[]
  corp_types: string[]
}
