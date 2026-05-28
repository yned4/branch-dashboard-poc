import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import type { MetaData, HealthData } from '../types'
import { KPICard } from '../components/KPICard'
import { AlertBox } from '../components/AlertBox'
import { SectionHeader } from '../components/SectionHeader'
import { FilterPanel, SelectField } from '../components/FilterPanel'
import { LineChartC, COLORS } from '../components/Charts'

interface Props { branchId: number; meta: MetaData }

export function HealthPage({ branchId, meta }: Props) {
  const [ym, setYm] = useState(meta.months[meta.months.length - 1])
  const { data, isLoading, error } = useQuery<HealthData>({
    queryKey: ['health', branchId, ym],
    queryFn: () => api.health({ branch_id: branchId, ym }) as Promise<HealthData>,
  })
  const branchName = meta.branches.find(b => b.支店ID === branchId)?.支店名 ?? ''

  const trendData = (data as any)?.trend_data?.map((d: any) => ({ 年月: d.年月, 月次粗利: d.月次粗利 })) ?? []

  return (
    <div className="p-6 max-w-6xl">
      <div className="mb-4">
        <h1 className="text-xl font-bold text-slate-800">ヘルスチェック — {branchName}</h1>
        <p className="text-xs text-slate-400 mt-1">今月、自支店は計画通りか／要注意指標は何か</p>
      </div>

      <FilterPanel>
        <SelectField label="集計月" value={ym} onChange={setYm} options={meta.months.map(m => ({ value: m, label: m }))} />
      </FilterPanel>

      {isLoading && <p className="text-slate-400 text-sm">読み込み中…</p>}
      {error && <p className="text-red-500 text-sm">データ取得エラー</p>}

      {data && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <KPICard label="月次粗利" value={`¥${data.kpis.monthly_gp.toLocaleString()}`}
              delta={`${data.kpis.monthly_gp_delta_pct >= 0 ? '+' : ''}${data.kpis.monthly_gp_delta_pct.toFixed(1)}% (YoY)`}
              deltaPositive={data.kpis.monthly_gp_delta_pct >= 0} />
            <KPICard label="仕入・仲介契約件数" value={`${data.kpis.contract_count}件`}
              delta={`${data.kpis.contract_count_delta >= 0 ? '+' : ''}${data.kpis.contract_count_delta}件 (YoY)`}
              deltaPositive={data.kpis.contract_count_delta >= 0} />
            <KPICard label="成約率" value={`${data.kpis.closing_rate.toFixed(1)}%`} />
            <KPICard label="1人当たり粗利" value={`¥${data.kpis.gp_per_person.toLocaleString()}`} />
          </div>

          <AlertBox alerts={data.alerts} />

          {trendData.length > 0 && (
            <>
              <SectionHeader id="health-trend" title="月次粗利トレンド（過去12ヶ月）" />
              <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
                <LineChartC data={trendData} xKey="年月"
                  lines={[{ key: '月次粗利', name: '月次粗利', color: COLORS.PRIMARY }]}
                  yFormat="yen" />
              </div>
            </>
          )}

          <SectionHeader id="health-guide" title="画面案内" />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-2">
            {[
              { label: 'メンバートラッカー', desc: '各営業の進捗・成長は同期対比でどうか' },
              { label: '情報入口分析', desc: 'どの情報源が効率高いか／メンバー別に偏りはないか' },
              { label: '売却出口分析', desc: '法人/個人・現況/再販構成は健全か' },
              { label: '契約・在庫分析', desc: '買取/仲介比率・サンタメ・在庫回転は適正か' },
              { label: '成長分析', desc: 'メンバーの成長カーブ／自支店の成熟段階' },
              { label: 'レビューエクスポート', desc: '本部月次報告用サマリー' },
            ].map(({ label, desc }) => (
              <div key={label} className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
                <p className="font-medium text-slate-700">{label}</p>
                <p className="text-xs text-slate-400 mt-1">{desc}</p>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
