import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import type { MetaData } from '../types'
import { AlertBox } from '../components/AlertBox'
import { SectionHeader } from '../components/SectionHeader'
import { FilterPanel, SelectField, MultiSelectField } from '../components/FilterPanel'
import { BarChartV, BarChartH, DonutChart, Histogram, COLORS } from '../components/Charts'
import { KPICard } from '../components/KPICard'

interface Props { branchId: number; meta: MetaData }

export function ExitAnalysisPage({ branchId, meta }: Props) {
  const last = meta.months.length - 1
  const [startYm, setStartYm] = useState(meta.months[Math.max(0, last - 11)])
  const [endYm, setEndYm] = useState(meta.months[last])
  const [selExit, setSelExit] = useState<string[]>([])
  const [selCorp, setSelCorp] = useState<string[]>([])

  const { data: raw, isLoading } = useQuery<any>({
    queryKey: ['exit-analysis', branchId, startYm, endYm, selExit, selCorp],
    queryFn: () => api.exitAnalysis({ branch_id: branchId, start_ym: startYm, end_ym: endYm, sel_exit: selExit.length ? selExit : undefined, sel_corp: selCorp.length ? selCorp : undefined }),
  })

  const branchName = meta.branches.find(b => b.支店ID === branchId)?.支店名 ?? ''

  return (
    <div className="p-6 max-w-6xl">
      <div className="mb-4">
        <h1 className="text-xl font-bold text-slate-800">売却出口分析 — {branchName}</h1>
        <p className="text-xs text-slate-400 mt-1">法人/個人・現況/再販構成は健全か／再販日数は適正か</p>
      </div>

      <FilterPanel>
        <SelectField label="開始月" value={startYm} onChange={setStartYm} options={meta.months.map(m => ({ value: m, label: m }))} />
        <SelectField label="終了月" value={endYm} onChange={setEndYm} options={meta.months.map(m => ({ value: m, label: m }))} />
        <MultiSelectField label="現況/再販" value={selExit} onChange={setSelExit} options={meta.exit_types} />
        <MultiSelectField label="法人/個人" value={selCorp} onChange={setSelCorp} options={meta.corp_types} />
      </FilterPanel>

      {isLoading && <p className="text-slate-400 text-sm">読み込み中…</p>}
      {raw && <AlertBox alerts={raw.alerts ?? []} />}

      {raw && (
        <>
          <SectionHeader id="2-1" title="法人・個人 売却先割合" />
          <div className="grid grid-cols-3 gap-4">
            {[
              { d: raw.corp_pie_this, title: `当月（${endYm}）` },
              { d: raw.corp_pie_ly,   title: '前年同月' },
              { d: raw.corp_pie_all,  title: '全支店平均（当月）' },
            ].map(({ d, title }) => d?.length > 0 && (
              <div key={title} className="bg-white rounded-xl border border-slate-200 shadow-sm">
                <DonutChart data={d.map((x: any) => ({ name: x.法人個人区分, value: x.件数 }))} title={title} />
              </div>
            ))}
          </div>

          <SectionHeader id="2-2" title="現況販売・リフォーム再販 割合推移（過去12ヶ月）" />
          {raw.resale_trend?.length > 0 && (() => {
            const types = [...new Set(raw.resale_trend.map((d: any) => d.現況再販区分))] as string[]
            const months = [...new Set(raw.resale_trend.map((d: any) => d.年月))].sort() as string[]
            const tData = months.map(m => {
              const row: Record<string, any> = { 年月: m }
              types.forEach(t => { row[t] = raw.resale_trend.find((d: any) => d.年月 === m && d.現況再販区分 === t)?.件数 ?? 0 })
              return row
            })
            return (
              <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
                <BarChartV data={tData} xKey="年月"
                  bars={types.map(t => ({ key: t, name: t, color: t === '再販' ? COLORS.PRIMARY : COLORS.PALE }))}
                  yFormat="num" stacked />
              </div>
            )
          })()}

          <SectionHeader id="2-3" title="リフォーム再販 平均粗利（支店比較）" />
          {raw.branch_gp?.length > 0 && (
            <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
              <BarChartH
                data={raw.branch_gp.map((d: any) => ({ ...d, 色: d.is_self ? COLORS.PRIMARY : COLORS.OTHER }))}
                yKey="支店名" xKey="平均粗利" xFormat="yen" colorKey="色" />
            </div>
          )}

          <SectionHeader id="2-4" title="リフォーム再販 平均売却日数" />
          {raw.avg_days != null && (
            <div className="grid grid-cols-2 gap-4 mb-4">
              <KPICard label="平均売却日数" value={`${Math.round(raw.avg_days)}日`} />
              <KPICard label="中央値" value={raw.med_days != null ? `${Math.round(raw.med_days)}日` : '-'} />
            </div>
          )}
          {raw.days_histogram?.length > 0 && (
            <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
              <Histogram
                data={raw.days_histogram.map((d: any) => d.在庫日数).filter((v: any) => v != null)}
                color={COLORS.PRIMARY}
                refLines={[
                  { x: raw.thresholds?.inv_warn ?? 120, label: `警告 ${raw.thresholds?.inv_warn ?? 120}日`, color: '#e08c00' },
                  { x: raw.thresholds?.inv_crit ?? 180, label: `要対応 ${raw.thresholds?.inv_crit ?? 180}日`, color: '#c0392b' },
                ]}
                xLabel="在庫日数" />
            </div>
          )}

          <SectionHeader id="2-5" title="出口別 値引き率" />
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-sm text-amber-700">
            想定売価カラムが未整備のため、現時点では計算不可。データ整備後に有効化。
          </div>
        </>
      )}
    </div>
  )
}
