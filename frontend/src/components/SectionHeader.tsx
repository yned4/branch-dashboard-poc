export function SectionHeader({ id, title }: { id: string; title: string }) {
  // "1-2/1-3" → "s-1-2-1-3" のようにHTML ID用に正規化
  const anchorId = id ? `s-${id.replace(/\//g, '-')}` : undefined
  return (
    <div id={anchorId} className="mt-8 mb-3 border-b border-slate-200 pb-2 scroll-mt-6">
      <h2 className="text-base font-semibold text-slate-700">
        <span className="text-slate-400 mr-2 text-sm">{id}</span>{title}
      </h2>
    </div>
  )
}
