import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import type { MetaData } from '../types'
import { AlertBox } from '../components/AlertBox'
import { SectionHeader } from '../components/SectionHeader'
import { FilterPanel, SelectField, MultiSelectField } from '../components/FilterPanel'
import { BarChartV, LineChartC, ScatterChartC, Histogram, COLORS } from '../components/Charts'
import { KPICard } from '../components/KPICard'

interface Props { branchId: number; meta: MetaData }

export function ContractsPage({ branchId, meta }: Props) {
  const last = meta.months.length - 1
  const [startYm, setStartYm] = useState(meta.months[Math.max(0, last - 11)])
  const [endYm, setEndYm] = useState(meta.months[last])
  const [selTypes, setSelTypes] = useState<string[]>([])
  const [selProps, setSelProps] = useState<string[]>([])
  const [selAreas, setSelAreas] = useState<string[]>([])

  const { data: raw, isLoading } = useQuery<any>({
    queryKey: ['contracts', branchId, startYm, endYm, selTypes, selProps, selAreas],
    queryFn: () => api.contracts({ branch_id: branchId, start_ym: startYm, end_ym: endYm, sel_keiyaku_types: selTypes.length ? selTypes : undefined, sel_prop_types: selProps.length ? selProps : undefined, sel_areas: selAreas.length ? selAreas : undefined }),
  })

  const branchName = meta.branches.find(b => b.支店ID === branchId)?.支店名 ?? ''

  return (
    <div className="p-6 max-w-6xl">
      <div className="mb-4">
        <h1 className="text-xl font-bold text-slate-800">契約・在庫分析 — {branchName}</h1>
        <p className="text-xs text-slate-400 mt-1">買取/仲介比率・サンタメ・在庫回転は適正か</p>
      </div>

      <FilterPanel>
        <SelectField label="開始月" value={startYm} onChange={setStartYm} options={meta.months.map(m => ({ value: m, label: m }))} />
        <SelectField label="終了月" value={endYm} onChange={setEndYm} options={meta.months.map(m => ({ value: m, label: m }))} />
        <MultiSelectField label="契約種別" value={selTypes} onChange={setSelTypes} options={['買取', '仲介', '売却']} />
        <MultiSelectField label="物件種別" value={selProps} onChange={setSelProps} options={meta.prop_types} />
        <MultiSelectField label="エリア" value={selAreas} onChange={setSelAreas} options={meta.areas} />
      </FilterPanel>

      {isLoading && <p className="text-slate-400 text-sm">読み込み中…</p>}
      {raw && <AlertBox alerts={raw.alerts ?? []} />}

      {raw && (
        <>
          <SectionHeader id="3-1" title="買取・仲介比率" />
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
              <p className="text-xs text-slate-500 mb-2">買取・仲介比率（当月）</p>
              <BarChartV
                data={['買取','仲介'].map(t => ({
                  種別: t,
                  [branchName]: raw.type_ratio?.self?.[t] ?? 0,
                  '全支店': raw.type_ratio?.all?.[t] ?? 0,
                }))}
                xKey="種別"
                bars={[{ key: branchName, name: branchName, color: COLORS.PRIMARY }, { key: '全支店', name: '全支店平均', color: COLORS.PALE }]}
                yFormat="pct" />
            </div>
            {(() => {
              const types = [...new Set((raw.trend ?? []).map((d: any) => d.契約種別))] as string[]
              const months = [...new Set((raw.trend ?? []).map((d: any) => d.年月))].sort() as string[]
              const tData = months.map(m => {
                const row: Record<string, any> = { 年月: m }
                types.forEach(t => { row[t] = raw.trend.find((d: any) => d.年月 === m && d.契約種別 === t)?.件数 ?? 0 })
                return row
              })
              return (
                <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
                  <p className="text-xs text-slate-500 mb-2">買取・仲介件数推移</p>
                  <BarChartV data={tData} xKey="年月"
                    bars={types.map((t, i) => ({ key: t, name: t, color: COLORS.BLUES_5[i % 5] }))}
                    yFormat="num" stacked />
                </div>
              )
            })()}
          </div>

          <SectionHeader id="3-2" title="サンタメ比率" />
          <div className="grid grid-cols-3 gap-4 mb-2">
            <KPICard label="サンタメ比率（当月）" value={`${(raw.santame?.pct ?? 0).toFixed(1)}%`} />
            <KPICard label="正常レンジ（仮置き）" value={`${raw.santame?.range?.lower ?? '-'}〜${raw.santame?.range?.upper ?? '-'}%`} />
            <KPICard label="ステータス" value={raw.santame?.level === 'ok' ? '正常' : '注意'} />
          </div>

          <SectionHeader id="3-3" title="契約件数（種別）月次推移" />
          {(() => {
            const types = [...new Set((raw.cnt_trend ?? []).map((d: any) => d.契約種別))] as string[]
            const months = [...new Set((raw.cnt_trend ?? []).map((d: any) => d.年月))].sort() as string[]
            const cData = months.map(m => {
              const row: Record<string, any> = { 年月: m }
              types.forEach(t => { row[t] = raw.cnt_trend.find((d: any) => d.年月 === m && d.契約種別 === t)?.件数 ?? 0 })
              return row
            })
            return (
              <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
                <LineChartC data={cData} xKey="年月"
                  lines={types.map((t, i) => ({ key: t, name: t, color: COLORS.BLUES_5[i % 5] }))}
                  yFormat="num" />
              </div>
            )
          })()}

          <SectionHeader id="3-4/3-5" title="支店別 1人当たり契約数・粗利（当月）" />
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
              <p className="text-xs text-slate-500 mb-2">1人当たり月次粗利</p>
              <BarChartV data={raw.branch_comparison ?? []} xKey="支店名"
                bars={[{ key: '1人当たり粗利', name: '粗利', color: COLORS.PRIMARY }]}
                yFormat="yen"
                refLines={[{ y: raw.thresholds?.gpp_warn ?? 0, label: '閾値' }]} />
            </div>
            <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
              <p className="text-xs text-slate-500 mb-2">1人当たり契約件数</p>
              <BarChartV data={raw.branch_comparison ?? []} xKey="支店名"
                bars={[{ key: '1人当たり契約数', name: '契約数', color: COLORS.MID }]}
                yFormat="num" />
            </div>
          </div>

          <SectionHeader id="3-6" title="在庫回転日数（分布）" />
          <div className="grid grid-cols-2 gap-4 mb-4">
            <KPICard label="在庫日数 中央値" value={`${Math.round(raw.inv_days?.中央値 ?? 0)}日`} />
            <KPICard label="在庫日数 平均" value={`${Math.round(raw.inv_days?.平均 ?? 0)}日`} />
          </div>
          {raw.inv_hist?.length > 0 && (
            <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
              <Histogram data={raw.inv_hist.map((d: any) => d.在庫日数)} color={COLORS.PRIMARY}
                refLines={[
                  { x: raw.thresholds?.inv_warn ?? 120, label: `警告 ${raw.thresholds?.inv_warn}日`, color: '#e08c00' },
                  { x: raw.thresholds?.inv_crit ?? 180, label: `要対応 ${raw.thresholds?.inv_crit}日`, color: '#c0392b' },
                ]} xLabel="在庫日数" />
            </div>
          )}

          <SectionHeader id="3-7" title="在庫回転率（年間）" />
          <KPICard label="年間在庫回転率（12ヶ月）" value={`${(raw.turnover_rate ?? 0).toFixed(2)}回転`} />

          <SectionHeader id="3-8" title="現金投下粗利率" />
          <div className="grid grid-cols-2 gap-4">
            <KPICard label="現金投下粗利率 平均" value={raw.cim?.avg != null ? `${raw.cim.avg.toFixed(1)}%` : 'データなし'} />
            <KPICard label="中央値" value={raw.cim?.median != null ? `${raw.cim.median.toFixed(1)}%` : '-'} />
          </div>

          <SectionHeader id="3-9" title="買取契約〜決済リードタイム" />
          <div className="grid grid-cols-2 gap-4 mb-4">
            <KPICard label="平均リードタイム" value={raw.leadtime?.avg != null ? `${Math.round(raw.leadtime.avg)}日` : 'データなし'} />
            <KPICard label="中央値" value={raw.leadtime?.median != null ? `${Math.round(raw.leadtime.median)}日` : '-'} />
          </div>
          {raw.lt_hist?.length > 0 && (
            <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
              <Histogram data={raw.lt_hist.map((d: any) => d.リードタイム)} color={COLORS.MID} xLabel="日数"
                refLines={[{ x: 60, label: '警告 60日', color: '#e08c00' }, { x: 90, label: '要対応 90日', color: '#c0392b' }]} />
            </div>
          )}

          <SectionHeader id="3-10" title="種別・エリア別 在庫回転日数 × 粗利率" />
          {raw.by_type?.length > 0 && (
            <>
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
                  <p className="text-xs text-slate-500 mb-2">種別別 平均在庫日数</p>
                  <BarChartV data={raw.by_type} xKey="種別"
                    bars={[{ key: '平均在庫日数', name: '平均', color: COLORS.PRIMARY }, { key: '中央値在庫日数', name: '中央値', color: COLORS.PALE }]}
                    yFormat="num" refLines={[{ y: raw.thresholds?.inv_warn ?? 120, label: `警告` }]} />
                </div>
                <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
                  <p className="text-xs text-slate-500 mb-2">種別別 平均粗利率（%）</p>
                  <BarChartV data={raw.by_type} xKey="種別"
                    bars={[{ key: '平均粗利率', name: '粗利率', color: COLORS.MID }]}
                    yFormat="pct" />
                </div>
              </div>
              {raw.by_type_area?.length > 0 && (
                <>
                  <p className="text-xs text-slate-400 mt-4 mb-1">▼ 種別×エリア 平均値散布図（右上が「得意ゾーン」）</p>
                  <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
                    <ScatterChartC
                      series={[...new Set(raw.by_type_area.map((d: any) => d.種別))].map((type: any, i) => ({
                        name: type,
                        color: COLORS.BLUES_5[i % 5],
                        data: raw.by_type_area.filter((d: any) => d.種別 === type).map((d: any) => ({
                          x: d.平均在庫日数, y: d.平均粗利率, z: d.件数, label: `${type} ${d.エリア}`
                        }))
                      }))}
                      xLabel="平均在庫日数（日）" yLabel="平均粗利率（%）"
                      yFormat="pct" refLineX={raw.thresholds?.inv_warn} height={400} />
                  </div>
                </>
              )}
            </>
          )}

          <SectionHeader id="3-11" title="長期滞留在庫 評価額比率（月末スナップショット）" />
          {raw.long_inventory && (
            <div className="grid grid-cols-2 gap-4">
              <KPICard label={`長期滞留在庫（${raw.thresholds?.inv_warn ?? 120}日超）評価額`} value={`¥${(raw.long_inventory.long_val ?? 0).toLocaleString()}`} />
              <KPICard label="全在庫に占める比率" value={`${(raw.long_inventory.long_pct ?? 0).toFixed(1)}%`} />
            </div>
          )}
        </>
      )}
    </div>
  )
}
