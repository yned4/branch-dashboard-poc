import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import type { MetaData } from '../types'
import { FilterPanel, SelectField } from '../components/FilterPanel'
import { KPICard } from '../components/KPICard'

interface Props { branchId: number; meta: MetaData }

export function ExportPage({ branchId, meta }: Props) {
  const [ym, setYm] = useState(meta.months[meta.months.length - 1])

  const { data, isLoading } = useQuery<any>({
    queryKey: ['export', branchId, ym],
    queryFn: () => api.exportData({ branch_id: branchId, ym }),
  })

  const branchName = meta.branches.find(b => b.支店ID === branchId)?.支店名 ?? ''

  const handleDownloadCSV = () => {
    if (!data?.kpi_table) return
    const rows = data.kpi_table
    const headers = Object.keys(rows[0])
    const csv = [headers.join(','), ...rows.map((r: any) => headers.map(h => r[h] ?? '').join(','))].join('\n')
    const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `月次レビュー_${branchName}_${ym}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleDownloadMD = () => {
    if (!data) return
    const lines = [
      `# 月次レビュー — ${branchName} (${ym})`,
      '',
      '## KPI サマリー',
      ...( data.kpi_table?.map((r: any) => `- **${r.指標}**: ${r.値}`) ?? []),
      '',
      '## 要注意メンバー',
      ...( data.watch_members?.map((r: any) => `- **${r.氏名}**: ${r['Next Action']}`) ?? []),
    ]
    const blob = new Blob([lines.join('\n')], { type: 'text/markdown;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `月次レビュー_${branchName}_${ym}.md`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="p-6 max-w-4xl">
      <div className="mb-4">
        <h1 className="text-xl font-bold text-slate-800">レビューエクスポート — {branchName}</h1>
        <p className="text-xs text-slate-400 mt-1">本部月次報告用サマリー</p>
      </div>

      <FilterPanel>
        <SelectField label="集計月" value={ym} onChange={setYm} options={meta.months.map(m => ({ value: m, label: m }))} />
      </FilterPanel>

      {isLoading && <p className="text-slate-400 text-sm">読み込み中…</p>}

      {data && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
            {data.kpi_table?.map((r: any) => (
              <KPICard key={r.指標} label={r.指標} value={r.値} delta={r.変化} deltaPositive={r.変化?.startsWith('+')} />
            ))}
          </div>

          {data.watch_members?.length > 0 && (
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-6">
              <p className="font-medium text-amber-800 mb-2">要注意メンバー</p>
              {data.watch_members.map((m: any) => (
                <div key={m.氏名} className="text-sm text-amber-700 mb-1">
                  <span className="font-medium">{m.氏名}</span>: {m['Next Action']}
                </div>
              ))}
            </div>
          )}

          <div className="flex gap-3">
            <button
              onClick={handleDownloadCSV}
              className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors"
            >
              CSV ダウンロード
            </button>
            <button
              onClick={handleDownloadMD}
              className="px-4 py-2 bg-slate-600 text-white text-sm rounded-lg hover:bg-slate-700 transition-colors"
            >
              Markdown ダウンロード
            </button>
          </div>
        </>
      )}
    </div>
  )
}
