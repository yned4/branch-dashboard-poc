interface Props {
  label: string
  value: string
  delta?: string
  deltaPositive?: boolean
}

export function KPICard({ label, value, delta, deltaPositive }: Props) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
      <p className="text-xs text-slate-500 mb-1">{label}</p>
      <p className="text-2xl font-semibold text-slate-800">{value}</p>
      {delta && (
        <p className={`text-xs mt-1 font-medium ${deltaPositive ? 'text-emerald-600' : 'text-rose-500'}`}>
          {delta}
        </p>
      )}
    </div>
  )
}
