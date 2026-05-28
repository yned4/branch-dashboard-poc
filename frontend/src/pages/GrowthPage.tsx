import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import type { MetaData, GrowthData } from '../types'
import { AlertBox } from '../components/AlertBox'
import { SectionHeader } from '../components/SectionHeader'
import { FilterPanel, SelectField, MultiSelectField } from '../components/FilterPanel'
import { LineChartC, BarChartV, COLORS } from '../components/Charts'

interface Props { branchId: number; meta: MetaData }

export function GrowthPage({ branchId, meta }: Props) {
  const last = meta.months.length - 1
  const [startYm, setStartYm] = useState(meta.months[Math.max(0, last - 11)])
  const [endYm, setEndYm] = useState(meta.months[last])
  const [selIndustries, setSelIndustries] = useState<string[]>([])

  const { data, isLoading } = useQuery<GrowthData>({
    queryKey: ['growth', branchId, startYm, endYm, selIndustries],
    queryFn: () => api.growth({ branch_id: branchId, start_ym: startYm, end_ym: endYm, sel_industries: selIndustries.length ? selIndustries : undefined }) as Promise<GrowthData>,
  })

  const branchName = meta.branches.find(b => b.支店ID === branchId)?.支店名 ?? ''

  return (
    <div className="p-6 max-w-6xl">
      <div className="mb-4">
        <h1 className="text-xl font-bold text-slate-800">成長分析 — {branchName}</h1>
        <p className="text-xs text-slate-400 mt-1">メンバーの成長カーブ／自支店の成熟段階／採用判断材料</p>
      </div>

      <FilterPanel>
        <SelectField label="開始月" value={startYm} onChange={setStartYm} options={meta.months.map(m => ({ value: m, label: m }))} />
        <SelectField label="終了月" value={endYm} onChange={setEndYm} options={meta.months.map(m => ({ value: m, label: m }))} />
        <div className="col-span-2">
          <MultiSelectField label="出身業種（成長分析用）" value={selIndustries} onChange={setSelIndustries} options={meta.industries} />
        </div>
      </FilterPanel>

      {isLoading && <p className="text-slate-400 text-sm">読み込み中…</p>}
      {data && <AlertBox alerts={data.alerts} />}

      {data && (
        <>
          <SectionHeader id="4-1" title="支店フェーズ別 成長分析" />
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
            {data.branch_phases.map(bp => (
              <div key={bp.支店名} className={`rounded-xl border p-4 ${bp.is_self ? 'border-blue-300 bg-blue-50' : 'border-slate-200 bg-white'}`}>
                <p className="text-xs text-slate-500">{bp.支店名}{bp.is_self ? '（自支店）' : ''}</p>
                <p className="font-semibold text-slate-800 mt-1">{(bp as any).フェーズ}</p>
                <p className="text-xs text-slate-400 mt-0.5">開設 {(bp as any).経過月数} ヶ月目</p>
              </div>
            ))}
          </div>

          {data.branch_gp_trend.length > 0 && (() => {
            const branches = [...new Set(data.branch_gp_trend.map(d => d.支店名))]
            const months = [...new Set(data.branch_gp_trend.map(d => d.年月))].sort()
            const trendData = months.map(m => {
              const row: Record<string, any> = { 年月: m }
              row['全支店平均'] = data.avg_by_month.find(d => d.年月 === m)?.月次粗利 ?? 0
              branches.forEach(b => { row[b] = data.branch_gp_trend.find(d => d.年月 === m && d.支店名 === b)?.月次粗利 ?? 0 })
              return row
            })
            const isSelfMap = Object.fromEntries(data.branch_gp_trend.map(d => [d.支店名, d.is_self]))
            return (
              <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
                <LineChartC data={trendData} xKey="年月"
                  lines={[
                    { key: '全支店平均', name: '全支店平均', color: COLORS.OTHER, dash: true },
                    ...branches.map((b, i) => ({
                      key: b, name: b,
                      color: isSelfMap[b] ? COLORS.SELF : COLORS.BLUES_5[(i + 1) % 5],
                      dash: !isSelfMap[b],
                    }))
                  ]}
                  yFormat="yen" />
              </div>
            )
          })()}

          <SectionHeader id="4-2" title="入社期別 コホート成長分析" />
          {(data as any).cohort_data?.length > 0 && (() => {
            const cohortRaw = (data as any).cohort_data
            const cohorts = [...new Set(cohortRaw.map((d: any) => d.入社期))] as string[]
            const elapseds = ([...new Set(cohortRaw.map((d: any) => d.経過月数))] as number[]).sort((a, b) => a - b)
            const cData = elapseds.map(e => {
              const row: Record<string, any> = { 経過月数: e }
              cohorts.forEach(c => { row[c] = cohortRaw.find((d: any) => d.経過月数 === e && d.入社期 === c)?.粗利_確定 ?? 0 })
              return row
            })
            return (
              <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
                <LineChartC data={cData} xKey="経過月数"
                  lines={cohorts.map((c, i) => ({ key: c, name: c, color: COLORS.BLUES_5[i % 5] }))}
                  yFormat="yen"
                  refLines={[{ y: data.thresholds.gpp_warn, label: '閾値' }]} />
              </div>
            )
          })()}

          <SectionHeader id="4-3" title="出身業種別 成長傾向（採用ターゲット参考）" />
          {(data as any).industry_data?.length > 0 && (() => {
            const indRaw = (data as any).industry_data
            const inds = [...new Set(indRaw.map((d: any) => d.出身業種))] as string[]
            const elapseds = ([...new Set(indRaw.map((d: any) => d.経過月数))] as number[]).sort((a, b) => a - b)
            const iData = elapseds.map(e => {
              const row: Record<string, any> = { 経過月数: e }
              inds.forEach(ind => { row[ind] = indRaw.find((d: any) => d.経過月数 === e && d.出身業種 === ind)?.粗利_確定 ?? 0 })
              return row
            })
            return (
              <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
                <LineChartC data={iData} xKey="経過月数"
                  lines={inds.map((ind, i) => ({ key: ind, name: ind, color: COLORS.BLUES_5[i % 5] }))}
                  yFormat="yen"
                  refLines={[{ y: data.thresholds.gpp_warn, label: '閾値' }]} />
              </div>
            )
          })()}
          <p className="text-xs text-slate-400 mt-1">HR向け参考指標。採用ターゲット選定の補助データとして活用。</p>

          <SectionHeader id="4-4" title="成長フェーズと情報源ポートフォリオ推移" />
          {data.tenure_src.length > 0 && (() => {
            const sources = [...new Set(data.tenure_src.map(d => d.情報源名))]
            const tenures = [...new Set(data.tenure_src.map(d => d.経験年次))].sort()
            const tsData = tenures.map(t => {
              const row: Record<string, any> = { 経験年次: t }
              sources.forEach(s => { row[s] = data.tenure_src.find(d => d.経験年次 === t && d.情報源名 === s)?.['割合(%)'] ?? 0 })
              return row
            })
            return (
              <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
                <BarChartV data={tsData} xKey="経験年次"
                  bars={sources.map((s, i) => ({ key: s, name: s, color: COLORS.BLUES_5[i % 5] }))}
                  yFormat="pct" stacked />
              </div>
            )
          })()}
        </>
      )}
    </div>
  )
}
