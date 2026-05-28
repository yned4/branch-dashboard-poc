import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import type { MetaData, MemberData, MemberRow } from '../types'
import { AlertBox } from '../components/AlertBox'
import { SectionHeader } from '../components/SectionHeader'
import { FilterPanel, SelectField, MultiSelectField } from '../components/FilterPanel'
import { BarChartV, LineChartC, ScatterChartC, COLORS } from '../components/Charts'

interface Props { branchId: number; meta: MetaData }

export function MembersPage({ branchId, meta }: Props) {
  const [ym, setYm] = useState(meta.months[meta.months.length - 1])
  const [selMembers, setSelMembers] = useState<string[]>([])

  const { data, isLoading } = useQuery<MemberData>({
    queryKey: ['members', branchId, ym],
    queryFn: () => api.members({ branch_id: branchId, ym }) as Promise<MemberData>,
  })

  const branchName = meta.branches.find(b => b.支店ID === branchId)?.支店名 ?? ''
  const allNames = data?.members.map(m => m.氏名) ?? []
  const filtered = data?.members.filter(m => selMembers.length === 0 || selMembers.includes(m.氏名)) ?? []
  const gppWarn = data?.thresholds.gpp_warn ?? 0
  const crWarn = data?.thresholds.cr_warn ?? 0

  const barData = filtered.map(m => ({ 氏名: m.氏名, 当月: m.粗利_確定, 前年同月: m.粗利_前年 }))
  const scatterData = [{
    name: 'メンバー',
    color: COLORS.PRIMARY,
    data: filtered.map(m => ({ x: m.経過月数, y: m.粗利_確定, z: m.契約件数, label: m.氏名 }))
  }]

  const rawCohort = (data as any)?.cohort_data ?? []
  const cohortYears = [...new Set(rawCohort.map((d: any) => d.入社年))] as string[]
  const cohortMonths = [...new Set(rawCohort.map((d: any) => d.年月))].sort() as string[]
  const cohortData = cohortMonths.map(m => {
    const row: Record<string, any> = { 年月: m }
    cohortYears.forEach(y => {
      const found = rawCohort.find((d: any) => d.年月 === m && d.入社年 === y)
      row[y] = found?.粗利_確定 ?? 0
    })
    return row
  })

  return (
    <div className="p-6 max-w-6xl">
      <div className="mb-4">
        <h1 className="text-xl font-bold text-slate-800">メンバートラッカー — {branchName}</h1>
        <p className="text-xs text-slate-400 mt-1">各営業の進捗・成長は同期対比でどうか／誰に何を指示すべきか</p>
      </div>

      <FilterPanel>
        <SelectField label="集計月" value={ym} onChange={setYm} options={meta.months.map(m => ({ value: m, label: m }))} />
        <div className="col-span-2">
          <MultiSelectField label="メンバー絞り込み（空=全員）" value={selMembers} onChange={setSelMembers} options={allNames} />
        </div>
      </FilterPanel>

      {isLoading && <p className="text-slate-400 text-sm">読み込み中…</p>}
      {data && <AlertBox alerts={data.alerts} />}

      {filtered.length > 0 && (
        <>
          <SectionHeader id="members-table" title="メンバー別実績（当月）" />
          <div className="overflow-x-auto bg-white rounded-xl border border-slate-200 shadow-sm">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 text-slate-500 text-xs">
                  {['氏名','経過月数','出身業種','雇用形態','契約件数','粗利','成約率'].map(h => (
                    <th key={h} className="px-4 py-3 text-left font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtered.map((m: MemberRow) => (
                  <tr key={m.社員ID} className="border-b border-slate-50 hover:bg-slate-50">
                    <td className="px-4 py-3 font-medium text-slate-700">{m.氏名}</td>
                    <td className="px-4 py-3 text-slate-500">{m.経過月数}ヶ月</td>
                    <td className="px-4 py-3 text-slate-500">{m.出身業種}</td>
                    <td className="px-4 py-3 text-slate-500">{m.雇用形態}</td>
                    <td className="px-4 py-3">{m.契約件数}</td>
                    <td className={`px-4 py-3 ${m.粗利_確定 < gppWarn ? 'bg-amber-50 text-amber-700 font-medium' : ''}`}>
                      ¥{m.粗利_確定.toLocaleString()}
                    </td>
                    <td className={`px-4 py-3 ${m.成約率 < crWarn ? 'bg-amber-50 text-amber-700 font-medium' : ''}`}>
                      {m.成約率.toFixed(1)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-xs text-slate-400 mt-1">黄色ハイライト = 閾値を下回り</p>

          <SectionHeader id="members-bar" title="粗利：当月 vs 前年同月" />
          <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
            <BarChartV data={barData} xKey="氏名"
              bars={[
                { key: '当月', name: '当月', color: COLORS.PRIMARY },
                { key: '前年同月', name: '前年同月', color: COLORS.PALE },
              ]}
              yFormat="yen"
              refLines={[{ y: gppWarn, label: `閾値 ¥${(gppWarn/10000).toFixed(0)}万` }]}
            />
          </div>

          <SectionHeader id="members-scatter" title="経過月数 × 粗利（成長軌跡）" />
          <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
            <ScatterChartC series={scatterData} xLabel="入社からの経過月数" yLabel="月次粗利（円）"
              yFormat="yen" refLineX={undefined} />
          </div>
        </>
      )}

      {cohortData.length > 0 && cohortYears.length > 0 && (
        <>
          <SectionHeader id="members-cohort" title="コホート別 平均粗利推移（過去12ヶ月）" />
          <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
            <LineChartC data={cohortData} xKey="年月"
              lines={cohortYears.map((y, i) => ({ key: y, name: y, color: COLORS.BLUES_5[i % 5] }))}
              yFormat="yen"
              refLines={[{ y: gppWarn, label: `閾値` }]}
            />
          </div>
        </>
      )}
    </div>
  )
}
