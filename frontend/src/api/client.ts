const BASE = '/api'

async function get<T>(path: string, params: Record<string, string | string[] | number | null | undefined> = {}): Promise<T> {
  const sp = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v == null) continue
    if (Array.isArray(v)) v.forEach(x => sp.append(k, x))
    else sp.append(k, String(v))
  }
  const url = `${BASE}${path}${sp.toString() ? '?' + sp.toString() : ''}`
  const res = await fetch(url)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

export const api = {
  meta: () => get('/meta'),
  health: (p: { branch_id: number; ym: string }) => get('/health', p),
  members: (p: { branch_id: number; ym: string }) => get('/members', p),
  infoSource: (p: { branch_id: number; start_ym: string; end_ym: string; sel_src?: string[] }) =>
    get('/info-source', { ...p, sel_src: p.sel_src }),
  exitAnalysis: (p: { branch_id: number; start_ym: string; end_ym: string; sel_exit?: string[]; sel_corp?: string[] }) =>
    get('/exit-analysis', p),
  contracts: (p: { branch_id: number; start_ym: string; end_ym: string; sel_keiyaku_types?: string[]; sel_prop_types?: string[]; sel_areas?: string[] }) =>
    get('/contracts', p),
  growth: (p: { branch_id: number; start_ym: string; end_ym: string; sel_industries?: string[] }) =>
    get('/growth', p),
  exportData: (p: { branch_id: number; ym: string }) => get('/export', p),
}
