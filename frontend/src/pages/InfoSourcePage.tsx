import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import type { MetaData, InfoSourceData } from '../types'
import { AlertBox } from '../components/AlertBox'
import { SectionHeader } from '../components/SectionHeader'
import { FilterPanel, SelectField, MultiSelectField } from '../components/FilterPanel'
import { BarChartH, BarChartV, DonutChart, COLORS } from '../components/Charts'

interface Props { branchId: number; meta: MetaData }

export function InfoSourcePage({ branchId, meta }: Props) {
  const last = meta.months.length - 1
  const [startYm, setStartYm] = useState(meta.months[Math.max(0, last - 11)])
  const [endYm, setEndYm] = useState(meta.months[last])
  const [selSrc, setSelSrc] = useState<string[]>([])

  const { data, isLoading } = useQuery<InfoSourceData>({
    queryKey: ['info-source', branchId, startYm, endYm, selSrc],
    queryFn: () => api.infoSource({ branch_id: branchId, start_ym: startYm, end_ym: endYm, sel_src: selSrc.length ? selSrc : undefined }) as Promise<InfoSourceData>,
  })

  const branchName = meta.branches.find(b => b.支店ID === branchId)?.支店名 ?? ''

  return (
    <div className="p-6 max-w-6xl">
      <div className="mb-4">
        <h1 className="text-xl font-bold text-slate-800">情報入口分析 — {branchName}</h1>
        <p className="text-xs text-slate-400 mt-1">どの情報源が効率高いか／メンバー別に偏りはないか</p>
      </div>

      <FilterPanel>
        <SelectField label="開始月" value={startYm} onChange={setStartYm} options={meta.months.map(m => ({ value: m, label: m }))} />
        <SelectField label="終了月" value={endYm} onChange={setEndYm} options={meta.months.map(m => ({ value: m, label: m }))} />
        <div className="col-span-2">
          <MultiSelectField label="情報源絞り込み（空=全件）" value={selSrc} onChange={setSelSrc} options={meta.info_sources} />
        </div>
      </FilterPanel>

      {isLoading && <p className="text-slate-400 text-sm">読み込み中…</p>}
      {data && <AlertBox alerts={data.alerts} />}

      {data && (
        <>
          <SectionHeader id="1-1" title="情報源別 月間案件数" />
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
              <BarChartH data={data.src_count} yKey="情報源名" xKey="月間平均案件数" xFormat="num" color={COLORS.PRIMARY} />
            </div>
            <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
              <DonutChart
                data={data.portfolio.map(d => ({ name: d.情報源名, value: d['依存度(%)'] }))}
                title={`情報源ポートフォリオ（${endYm}）`}
              />
            </div>
          </div>

          <SectionHeader id="1-2/1-3" title="情報源別 成約率 & 平均粗利" />
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
              <p className="text-xs text-slate-500 mb-2">情報源別 成約率</p>
              <BarChartH data={data.src_stats} yKey="情報源名" xKey="成約率(%)" xFormat="pct" color={COLORS.MID} />
            </div>
            <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
              <p className="text-xs text-slate-500 mb-2">情報源別 平均粗利</p>
              <BarChartH data={data.src_stats} yKey="情報源名" xKey="平均粗利" xFormat="yen" color={COLORS.LIGHT} />
            </div>
          </div>

          <SectionHeader id="1-4" title="入社経過月数別 情報源ポートフォリオ推移" />
          {data.tenure_src.length > 0 && (() => {
            const sources = [...new Set(data.tenure_src.map(d => d.情報源名))]
            const tenures = [...new Set(data.tenure_src.map(d => d.経験年次))].sort()
            const tData = tenures.map(t => {
              const row: Record<string, any> = { 経験年次: t }
              sources.forEach(s => { row[s] = data.tenure_src.find(d => d.経験年次 === t && d.情報源名 === s)?.案件数 ?? 0 })
              return row
            })
            return (
              <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
                <BarChartV data={tData} xKey="経験年次"
                  bars={sources.map((s, i) => ({ key: s, name: s, color: COLORS.BLUES_5[i % 5] }))}
                  yFormat="num" stacked />
              </div>
            )
          })()}

          <SectionHeader id="1-5" title="案件化〜初回契約 リードタイム（情報源別）" />
          <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
            <BarChartV data={data.leadtime} xKey="情報源名"
              bars={[
                { key: '平均日数', name: '平均', color: COLORS.PRIMARY },
                { key: '中央値', name: '中央値', color: COLORS.PALE },
              ]}
              yFormat="num" />
          </div>

          <SectionHeader id="1-6" title="情報源別 コスト調整後 ROI" />
          <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
            <BarChartH data={data.roi} yKey="情報源名" xKey="ROI" xFormat="yen" color={COLORS.SELF} />
          </div>
        </>
      )}
    </div>
  )
}
