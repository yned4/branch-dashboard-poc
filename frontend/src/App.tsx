import { useState } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useQuery } from '@tanstack/react-query'
import { api } from './api/client'
import type { MetaData } from './types'
import { Sidebar } from './components/Sidebar'
import { ChatWidget } from './components/ChatWidget'
import { HealthPage } from './pages/HealthPage'
import { MembersPage } from './pages/MembersPage'
import { InfoSourcePage } from './pages/InfoSourcePage'
import { ExitAnalysisPage } from './pages/ExitAnalysisPage'
import { ContractsPage } from './pages/ContractsPage'
import { GrowthPage } from './pages/GrowthPage'
import { ExportPage } from './pages/ExportPage'

const qc = new QueryClient({ defaultOptions: { queries: { staleTime: 60_000, retry: 1 } } })

function Dashboard() {
  const { data: meta, isLoading } = useQuery<MetaData>({ queryKey: ['meta'], queryFn: () => api.meta() as Promise<MetaData> })
  const [branchId, setBranchId] = useState<number | null>(null)

  if (isLoading || !meta) return (
    <div className="flex items-center justify-center flex-1 text-slate-400">データ読み込み中…</div>
  )

  const effectiveBranchId = branchId ?? meta.branches[0].支店ID
  const props = { branchId: effectiveBranchId, meta }

  return (
    <div className="flex flex-1 h-full overflow-hidden">
      <Sidebar
        branches={meta.branches}
        branchId={effectiveBranchId}
        onBranchChange={setBranchId}
      />
      <main className="flex-1 overflow-auto bg-slate-50">
        <Routes>
          <Route path="/"          element={<HealthPage {...props} />} />
          <Route path="/members"   element={<MembersPage {...props} />} />
          <Route path="/info"      element={<InfoSourcePage {...props} />} />
          <Route path="/exit"      element={<ExitAnalysisPage {...props} />} />
          <Route path="/contracts" element={<ContractsPage {...props} />} />
          <Route path="/growth"    element={<GrowthPage {...props} />} />
          <Route path="/export"    element={<ExportPage {...props} />} />
        </Routes>
      </main>
      <ChatWidget branchId={effectiveBranchId} ym={meta.months[meta.months.length - 1]} />
    </div>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <Dashboard />
      </BrowserRouter>
    </QueryClientProvider>
  )
}
