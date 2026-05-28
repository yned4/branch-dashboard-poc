import { NavLink } from 'react-router-dom'
import type { Branch } from '../types'

function IconHealth() {
  return <svg className="w-[18px] h-[18px] shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12" /></svg>
}
function IconUsers() {
  return <svg className="w-[18px] h-[18px] shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
}
function IconBarChart() {
  return <svg className="w-[18px] h-[18px] shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
}
function IconLogOut() {
  return <svg className="w-[18px] h-[18px] shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
}
function IconClipboard() {
  return <svg className="w-[18px] h-[18px] shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1" ry="1"/></svg>
}
function IconTrendingUp() {
  return <svg className="w-[18px] h-[18px] shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>
}
function IconDownload() {
  return <svg className="w-[18px] h-[18px] shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
}

const NAV = [
  { to: '/',          icon: <IconHealth />,     label: 'ヘルスチェック' },
  { to: '/members',   icon: <IconUsers />,      label: 'メンバートラッカー' },
  { to: '/info',      icon: <IconBarChart />,   label: '情報入口分析' },
  { to: '/exit',      icon: <IconLogOut />,     label: '売却出口分析' },
  { to: '/contracts', icon: <IconClipboard />,  label: '契約・在庫分析' },
  { to: '/growth',    icon: <IconTrendingUp />, label: '成長分析' },
  { to: '/export',    icon: <IconDownload />,   label: 'レビューエクスポート' },
]

interface Props {
  branches: Branch[]
  branchId: number
  onBranchChange: (id: number) => void
}

export function Sidebar({ branches, branchId, onBranchChange }: Props) {
  return (
    <aside className="w-56 shrink-0 flex flex-col h-full overflow-y-auto" style={{ background: '#1e2330' }}>
      {/* ロゴ */}
      <div className="px-5 pt-5 pb-4" style={{ borderBottom: '1px solid #2d3448' }}>
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded flex items-center justify-center shrink-0" style={{ background: '#2563a8' }}>
            <svg className="w-4 h-4 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>
            </svg>
          </div>
          <div>
            <p className="text-white font-semibold text-sm tracking-wide leading-none">MARKS</p>
            <p className="text-xs leading-none mt-1" style={{ color: '#6b7899' }}>Analytics</p>
          </div>
        </div>
      </div>

      {/* 支店セレクター */}
      <div className="px-4 py-3.5" style={{ borderBottom: '1px solid #2d3448' }}>
        <p className="text-xs font-medium mb-1.5 uppercase tracking-wider" style={{ color: '#6b7899' }}>支店</p>
        <select
          className="w-full text-sm rounded px-2 py-1.5 outline-none focus:ring-1"
          style={{ background: '#252b3b', color: '#c9d1e0', border: '1px solid #3a4257' }}
          value={branchId}
          onChange={e => onBranchChange(Number(e.target.value))}
        >
          {branches.map(b => (
            <option key={b.支店ID} value={b.支店ID}>{b.支店名}</option>
          ))}
        </select>
      </div>

      {/* ナビゲーション */}
      <nav className="flex-1 py-2">
        <p className="px-4 pt-3 pb-1 text-xs font-medium uppercase tracking-wider" style={{ color: '#6b7899' }}>レポート</p>
        {NAV.map(({ to, icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-2.5 text-sm transition-colors border-l-2 ${
                isActive
                  ? 'border-blue-400 text-white'
                  : 'border-transparent hover:text-slate-200'
              }`
            }
            style={({ isActive }) => ({
              background: isActive ? 'rgba(37,99,168,0.18)' : undefined,
              color: isActive ? '#e2e8f0' : '#8896b3',
            })}
          >
            {icon}
            <span className="leading-none">{label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="px-4 py-3" style={{ borderTop: '1px solid #2d3448' }}>
        <p className="text-xs" style={{ color: '#3d4d6a' }}>不動産買取再販 v1.0</p>
      </div>
    </aside>
  )
}
