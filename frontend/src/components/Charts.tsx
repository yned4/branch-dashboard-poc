import {
  LineChart, Line, BarChart, Bar, ScatterChart, Scatter,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  PieChart, Pie, Cell, ReferenceLine, Label
} from 'recharts'

export const COLORS = {
  SELF:    '#1a3a6b',
  PRIMARY: '#2563a8',
  MID:     '#4a90d9',
  LIGHT:   '#7fb3e8',
  PALE:    '#b8d9f7',
  OTHER:   '#b0b8c8',
  BLUES_5: ['#1a3a6b', '#2563a8', '#4a90d9', '#7fb3e8', '#b8d9f7'],
}

const fmt = (v: number) => v.toLocaleString()
const fmtJP = (v: number) => {
  if (v >= 100_000_000) return `${(v / 100_000_000).toFixed(1)}億`
  if (v >= 10_000)      return `${Math.round(v / 10_000)}万`
  return v.toLocaleString()
}
const fmtYen = (v: number) => `¥${fmtJP(v)}`
const fmtPct = (v: number) => `${v.toFixed(1)}%`

// ── Line Chart ────────────────────────────────────────────
interface LineProps {
  data: Record<string, any>[]
  xKey: string
  lines: { key: string; name: string; color: string; dash?: boolean }[]
  height?: number
  yFormat?: 'yen' | 'pct' | 'num'
  refLines?: { y: number; label: string }[]
}

export function LineChartC({ data, xKey, lines, height = 300, yFormat = 'yen', refLines = [] }: LineProps) {
  const tickFmt = yFormat === 'yen' ? fmtYen : yFormat === 'pct' ? fmtPct : fmt
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 8, right: 16, left: 16, bottom: 40 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis dataKey={xKey} tick={{ fontSize: 10, angle: -35, textAnchor: 'end', dy: 4 }} height={56} interval="preserveStartEnd" />
        <YAxis tickFormatter={tickFmt} tick={{ fontSize: 11 }} width={70} />
        <Tooltip formatter={(v: any) => tickFmt(v)} />
        <Legend wrapperStyle={{ fontSize: 11 }} />
        {refLines.map(r => (
          <ReferenceLine key={r.y} y={r.y} stroke="#e08c00" strokeDasharray="4 4">
            <Label value={r.label} position="right" fontSize={10} fill="#e08c00" />
          </ReferenceLine>
        ))}
        {lines.map(l => (
          <Line key={l.key} dataKey={l.key} name={l.name} stroke={l.color}
            strokeWidth={2} dot={false} strokeDasharray={l.dash ? '5 3' : undefined} />
        ))}
      </LineChart>
    </ResponsiveContainer>
  )
}

// ── Bar Chart (vertical) ──────────────────────────────────
interface BarVProps {
  data: Record<string, any>[]
  xKey: string
  bars: { key: string; name: string; color: string }[]
  height?: number
  yFormat?: 'yen' | 'pct' | 'num'
  stacked?: boolean
  refLines?: { y: number; label: string }[]
}

export function BarChartV({ data, xKey, bars, height = 280, yFormat = 'yen', stacked = false, refLines = [] }: BarVProps) {
  const tickFmt = yFormat === 'yen' ? fmtYen : yFormat === 'pct' ? fmtPct : fmt
  const needsRotate = data.length > 5
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 8, right: 16, left: 16, bottom: needsRotate ? 40 : 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis dataKey={xKey}
          tick={needsRotate ? { fontSize: 10, angle: -35, textAnchor: 'end', dy: 4 } : { fontSize: 11 }}
          height={needsRotate ? 56 : 30}
          interval={needsRotate ? 'preserveStartEnd' : 0} />
        <YAxis tickFormatter={tickFmt} tick={{ fontSize: 11 }} width={70} />
        <Tooltip formatter={(v: any) => tickFmt(v)} />
        <Legend wrapperStyle={{ fontSize: 11 }} />
        {refLines.map(r => (
          <ReferenceLine key={r.y} y={r.y} stroke="#e08c00" strokeDasharray="4 4">
            <Label value={r.label} position="right" fontSize={10} fill="#e08c00" />
          </ReferenceLine>
        ))}
        {bars.map(b => (
          <Bar key={b.key} dataKey={b.key} name={b.name} fill={b.color}
            stackId={stacked ? 'stack' : undefined} />
        ))}
      </BarChart>
    </ResponsiveContainer>
  )
}

// ── Bar Chart (horizontal) ────────────────────────────────
interface BarHProps {
  data: Record<string, any>[]
  yKey: string
  xKey: string
  name?: string
  colorKey?: string  // per-bar colors from data field
  color?: string
  height?: number
  xFormat?: 'yen' | 'pct' | 'num'
  refLines?: { x: number; label: string }[]
}

export function BarChartH({ data, yKey, xKey, name, colorKey, color = COLORS.PRIMARY, height = 280, xFormat = 'yen', refLines = [] }: BarHProps) {
  const tickFmt = xFormat === 'yen' ? fmtYen : xFormat === 'pct' ? fmtPct : fmt
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} layout="vertical" margin={{ top: 8, right: 16, left: 8, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis type="number" tickFormatter={tickFmt} tick={{ fontSize: 11 }} />
        <YAxis type="category" dataKey={yKey} tick={{ fontSize: 11 }} width={90} />
        <Tooltip formatter={(v: any) => tickFmt(v)} />
        {refLines.map(r => (
          <ReferenceLine key={r.x} x={r.x} stroke="#e08c00" strokeDasharray="4 4">
            <Label value={r.label} position="top" fontSize={10} fill="#e08c00" />
          </ReferenceLine>
        ))}
        <Bar dataKey={xKey} name={name ?? xKey} fill={color}>
          {colorKey && data.map((d, i) => <Cell key={i} fill={d[colorKey] ?? color} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

// ── Pie / Donut Chart ─────────────────────────────────────
interface PieProps {
  data: { name: string; value: number }[]
  colors?: string[]
  height?: number
  title?: string
}

export function DonutChart({ data, colors = COLORS.BLUES_5, height = 260, title }: PieProps) {
  return (
    <div>
      {title && <p className="text-xs text-slate-500 text-center mb-1">{title}</p>}
      <ResponsiveContainer width="100%" height={height}>
        <PieChart>
          <Pie data={data} cx="50%" cy="50%" innerRadius="40%" outerRadius="70%"
            dataKey="value" nameKey="name" label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
            labelLine={false} fontSize={11}>
            {data.map((_, i) => <Cell key={i} fill={colors[i % colors.length]} />)}
          </Pie>
          <Tooltip formatter={(v: any) => v} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}

// ── Scatter Chart ─────────────────────────────────────────
interface ScatterProps {
  series: { name: string; data: { x: number; y: number; z?: number; label?: string }[]; color: string }[]
  xLabel?: string
  yLabel?: string
  height?: number
  xFormat?: 'num' | 'yen'
  yFormat?: 'num' | 'pct' | 'yen'
  refLineX?: number
}

export function ScatterChartC({ series, xLabel, yLabel, height = 380, xFormat = 'num', yFormat = 'pct', refLineX }: ScatterProps) {
  const xFmt = xFormat === 'yen' ? fmtYen : fmt
  const yFmt = yFormat === 'yen' ? fmtYen : yFormat === 'pct' ? fmtPct : fmt
  return (
    <ResponsiveContainer width="100%" height={height}>
      <ScatterChart margin={{ top: 32, right: 24, left: 24, bottom: xLabel ? 36 : 16 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis type="number" dataKey="x" name={xLabel} tickFormatter={xFmt} tick={{ fontSize: 11 }} height={xLabel ? 44 : 30}>
          {xLabel && <Label value={xLabel} position="bottom" offset={0} fontSize={11} fill="#64748b" />}
        </XAxis>
        <YAxis type="number" dataKey="y" name={yLabel} tickFormatter={yFmt} tick={{ fontSize: 11 }} width={80}>
          {yLabel && <Label value={yLabel} angle={-90} position="insideLeft" offset={16} fontSize={11} fill="#64748b" />}
        </YAxis>
        <Tooltip cursor={{ strokeDasharray: '3 3' }}
          content={({ payload }) => {
            if (!payload?.length) return null
            const d = payload[0].payload
            return (
              <div className="bg-white border border-slate-200 rounded px-2 py-1 text-xs shadow">
                {d.label && <p className="font-medium">{d.label}</p>}
                <p>{xLabel}: {xFmt(d.x)}</p>
                <p>{yLabel}: {yFmt(d.y)}</p>
                {d.z && <p>件数: {d.z}</p>}
              </div>
            )
          }}
        />
        <Legend verticalAlign="top" wrapperStyle={{ fontSize: 11, paddingBottom: 8 }} />
        {refLineX != null && (
          <ReferenceLine x={refLineX} stroke="#e08c00" strokeDasharray="4 4">
            <Label value={`警告 ${refLineX}日`} position="top" fontSize={10} fill="#e08c00" />
          </ReferenceLine>
        )}
        {series.map(s => (
          <Scatter key={s.name} name={s.name} data={s.data} fill={s.color} opacity={0.85} />
        ))}
      </ScatterChart>
    </ResponsiveContainer>
  )
}

// ── Histogram (bin approximation) ────────────────────────
interface HistProps {
  data: number[]
  bins?: number
  color?: string
  height?: number
  refLines?: { x: number; label: string; color?: string }[]
  xLabel?: string
}

export function Histogram({ data, bins = 20, color = COLORS.PRIMARY, height = 280, refLines = [], xLabel }: HistProps) {
  if (!data.length) return null
  const min = Math.min(...data), max = Math.max(...data)
  const binW = (max - min) / bins || 1
  const counts: { x: number; count: number }[] = Array.from({ length: bins }, (_, i) => ({
    x: Math.round(min + i * binW),
    count: 0,
  }))
  data.forEach(v => {
    const idx = Math.min(Math.floor((v - min) / binW), bins - 1)
    counts[idx].count++
  })
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={counts} margin={{ top: 8, right: 16, left: 8, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis dataKey="x" tick={{ fontSize: 11 }}>
          {xLabel && <Label value={xLabel} position="insideBottom" offset={-4} fontSize={11} />}
        </XAxis>
        <YAxis tick={{ fontSize: 11 }} />
        <Tooltip />
        {refLines.map(r => (
          <ReferenceLine key={r.x} x={r.x} stroke={r.color ?? '#e08c00'} strokeDasharray="4 4">
            <Label value={r.label} position="top" fontSize={10} fill={r.color ?? '#e08c00'} />
          </ReferenceLine>
        ))}
        <Bar dataKey="count" fill={color} name="件数" />
      </BarChart>
    </ResponsiveContainer>
  )
}
