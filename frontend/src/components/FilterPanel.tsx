import { useState, ReactNode } from 'react'
import { ChevronDown, ChevronUp, SlidersHorizontal } from 'lucide-react'

interface Props {
  children: ReactNode
  defaultOpen?: boolean
}

export function FilterPanel({ children, defaultOpen = true }: Props) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="bg-white border border-slate-200 rounded-xl shadow-sm mb-6">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center gap-2 px-4 py-3 text-sm font-medium text-slate-600 hover:bg-slate-50 rounded-xl"
      >
        <SlidersHorizontal size={15} />
        フィルター
        <span className="ml-auto">{open ? <ChevronUp size={15} /> : <ChevronDown size={15} />}</span>
      </button>
      {open && <div className="px-4 pb-4 grid grid-cols-2 md:grid-cols-4 gap-4">{children}</div>}
    </div>
  )
}

export function FilterField({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <label className="block text-xs text-slate-500 mb-1">{label}</label>
      {children}
    </div>
  )
}

const selectCls = "w-full text-sm border border-slate-200 rounded-lg px-3 py-2 bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-300"

export function SelectField({ label, value, onChange, options }: {
  label: string
  value: string
  onChange: (v: string) => void
  options: { value: string; label: string }[]
}) {
  return (
    <FilterField label={label}>
      <select className={selectCls} value={value} onChange={e => onChange(e.target.value)}>
        {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </FilterField>
  )
}

export function MultiSelectField({ label, value, onChange, options }: {
  label: string
  value: string[]
  onChange: (v: string[]) => void
  options: string[]
}) {
  const toggle = (opt: string) => {
    onChange(value.includes(opt) ? value.filter(v => v !== opt) : [...value, opt])
  }
  const all = value.length === 0 || value.length === options.length
  return (
    <FilterField label={label}>
      <div className="flex flex-wrap gap-1 mt-1">
        <button
          onClick={() => onChange([])}
          className={`text-xs px-2 py-1 rounded-full border ${all ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-slate-600 border-slate-300'}`}
        >
          全件
        </button>
        {options.map(o => (
          <button
            key={o}
            onClick={() => toggle(o)}
            className={`text-xs px-2 py-1 rounded-full border ${(!all && value.includes(o)) ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-slate-600 border-slate-300'}`}
          >
            {o}
          </button>
        ))}
      </div>
    </FilterField>
  )
}
