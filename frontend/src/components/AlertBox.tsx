import type { Alert } from '../types'

export function AlertBox({ alerts }: { alerts: Alert[] }) {
  if (!alerts.length) return null
  return (
    <div className="space-y-2 my-4">
      {alerts.map((a, i) => (
        <div
          key={i}
          className={`flex items-start gap-2.5 rounded-lg px-4 py-3 text-sm border ${
            a.level === 'critical'
              ? 'bg-red-50 border-red-300 text-red-800'
              : 'bg-amber-50 border-amber-300 text-amber-800'
          }`}
        >
          <span className={`mt-0.5 w-2 h-2 rounded-full shrink-0 ${a.level === 'critical' ? 'bg-red-500' : 'bg-amber-400'}`} />
          <span>
            <strong>{a.level === 'critical' ? 'Next Action（要対応）' : 'Next Action（注意）'}：</strong>
            {a.message}
          </span>
        </div>
      ))}
    </div>
  )
}
