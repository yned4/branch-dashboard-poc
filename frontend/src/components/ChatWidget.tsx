import { useState, useRef, useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

interface Props {
  branchId: number
  ym: string
}

// セクション単位のリンク定義
// anchorId は SectionHeader の id prop を "s-" + スラッシュ→ハイフン変換したもの
interface SectionLink {
  path: string
  anchorId: string  // "" = ページトップ
  label: string
  keywords: string[]
}

const SECTION_LINKS: SectionLink[] = [
  // ヘルスチェック
  { path: '/', anchorId: 's-health-trend', label: '月次粗利トレンド', keywords: ['月次粗利', 'トレンド', '推移', 'ヘルスチェック'] },

  // メンバートラッカー
  { path: '/members', anchorId: 's-members-table', label: 'メンバー別実績一覧', keywords: ['メンバー実績', '成約率', '社員', '営業 一覧'] },
  { path: '/members', anchorId: 's-members-bar',   label: '粗利 当月vs前年',    keywords: ['前年', '前年比', '粗利 比較'] },
  { path: '/members', anchorId: 's-members-scatter',label: '成長軌跡（散布図）', keywords: ['成長軌跡', '経過月数', '粗利 月数'] },
  { path: '/members', anchorId: 's-members-cohort', label: 'コホート別粗利推移', keywords: ['コホート', '入社期', 'コホート 粗利'] },

  // 情報入口分析
  { path: '/info', anchorId: 's-1-1',       label: '情報源別 月間案件数',     keywords: ['情報源 件数', '案件数', '情報源 案件'] },
  { path: '/info', anchorId: 's-1-2-1-3',   label: '情報源別 成約率・粗利',   keywords: ['情報源 成約率', '情報源 粗利', '成約率 情報'] },
  { path: '/info', anchorId: 's-1-4',       label: '経験年次別 情報源推移',   keywords: ['経験年次', '年次 情報源'] },
  { path: '/info', anchorId: 's-1-5',       label: '案件化〜契約 リードタイム', keywords: ['リードタイム', '案件化', '初回契約'] },
  { path: '/info', anchorId: 's-1-6',       label: '情報源別 ROI',            keywords: ['ROI', 'コスト', '費用対効果', 'コスト調整'] },

  // 売却出口分析
  { path: '/exit', anchorId: 's-2-1', label: '法人・個人 売却先割合',    keywords: ['法人', '個人', '売却先', '法人 個人'] },
  { path: '/exit', anchorId: 's-2-2', label: '現況・再販 割合推移',      keywords: ['再販', '現況販売', 'リフォーム 再販', '現況 再販'] },
  { path: '/exit', anchorId: 's-2-3', label: 'リフォーム再販 平均粗利', keywords: ['リフォーム 粗利', '再販 粗利', '再販 平均'] },
  { path: '/exit', anchorId: 's-2-4', label: 'リフォーム再販 売却日数', keywords: ['売却日数', '売却期間', '再販 日数'] },

  // 契約・在庫分析
  { path: '/contracts', anchorId: 's-3-1',    label: '買取・仲介 比率',         keywords: ['買取', '仲介', '買取 仲介', '比率 契約'] },
  { path: '/contracts', anchorId: 's-3-2',    label: 'サンタメ比率',            keywords: ['サンタメ'] },
  { path: '/contracts', anchorId: 's-3-3',    label: '契約件数 月次推移',       keywords: ['契約件数', '契約 推移', '月次 件数'] },
  { path: '/contracts', anchorId: 's-3-4-3-5',label: '1人当たり契約数・粗利',  keywords: ['1人当たり', '人当たり', '支店比較 粗利'] },
  { path: '/contracts', anchorId: 's-3-6',    label: '在庫回転日数 分布',       keywords: ['在庫回転', '在庫日数', '滞留 分布', '回転日数'] },
  { path: '/contracts', anchorId: 's-3-7',    label: '在庫回転率（年間）',      keywords: ['回転率', '年間 回転'] },
  { path: '/contracts', anchorId: 's-3-8',    label: '現金投下粗利率',          keywords: ['現金投下', 'CIM', '投下'] },
  { path: '/contracts', anchorId: 's-3-9',    label: '買取〜決済 リードタイム', keywords: ['買取 リードタイム', '決済 リードタイム', '買取 決済'] },
  { path: '/contracts', anchorId: 's-3-10',   label: '種別×エリア 散布図',     keywords: ['エリア', '散布図', '種別 エリア', 'バブル'] },
  { path: '/contracts', anchorId: 's-3-11',   label: '長期滞留在庫 評価額',     keywords: ['長期滞留', '長期 在庫', '評価額'] },

  // 成長分析
  { path: '/growth', anchorId: 's-4-1', label: '支店フェーズ',          keywords: ['フェーズ', '成熟期', '成長期', '新規出店', '支店 段階'] },
  { path: '/growth', anchorId: 's-4-2', label: 'コホート成長分析',      keywords: ['コホート 成長', '入社期 成長', '成長 コホート'] },
  { path: '/growth', anchorId: 's-4-3', label: '出身業種別 成長傾向',   keywords: ['出身業種', '採用', '業種 成長'] },
  { path: '/growth', anchorId: 's-4-4', label: '情報源ポートフォリオ推移', keywords: ['ポートフォリオ 推移', '経験 情報源', '年次 ポートフォリオ'] },
]

function detectSections(text: string): SectionLink[] {
  const scored = SECTION_LINKS.map(s => ({
    ...s,
    score: s.keywords.filter(kw =>
      kw.split(' ').every(word => text.includes(word))
    ).length,
  }))
  return scored
    .filter(s => s.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, 3)
}

function pageFromPath(path: string): string {
  const seg = path.split('/')[1]
  return seg || 'health'
}

export function ChatWidget({ branchId, ym }: Props) {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const location = useLocation()
  const navigate = useNavigate()
  const page = pageFromPath(location.pathname)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    if (open) inputRef.current?.focus()
  }, [open])

  function navigateToSection(path: string, anchorId: string) {
    setOpen(false)
    navigate(path)
    if (anchorId) {
      // ページ遷移後にスクロール（React Queryのキャッシュがあれば即座に描画）
      setTimeout(() => {
        document.getElementById(anchorId)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }, 150)
    }
  }

  async function send() {
    const text = input.trim()
    if (!text || streaming) return
    setInput('')

    const next: Message[] = [...messages, { role: 'user', content: text }]
    setMessages(next)
    setStreaming(true)

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ branch_id: branchId, ym, messages: next, page }),
      })
      const obj = await res.json().catch(() => ({} as any))
      if (!res.ok) throw new Error(obj?.error || `${res.status} ${res.statusText}`)
      if (obj?.error) throw new Error(obj.error)
      const reply = (obj?.text ?? '').toString()
      setMessages(m => [...m, { role: 'assistant', content: reply || '（応答が空でした）' }])
    } catch (e: any) {
      setMessages(m => [...m, { role: 'assistant', content: `接続エラー: ${e.message}` }])
    } finally {
      setStreaming(false)
    }
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  return (
    <>
      {/* フローティングボタン */}
      <button
        onClick={() => setOpen(o => !o)}
        className="fixed bottom-6 right-6 z-50 w-12 h-12 rounded-full shadow-lg flex items-center justify-center transition-transform hover:scale-105 active:scale-95"
        style={{ background: '#2563a8' }}
        title="アシスタントに質問"
      >
        {open ? (
          <svg className="w-5 h-5 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        ) : (
          <svg className="w-5 h-5 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
          </svg>
        )}
      </button>

      {/* チャットパネル */}
      {open && (
        <div
          className="fixed z-50 flex flex-col rounded-xl shadow-2xl overflow-hidden"
          style={{ width: 360, height: 500, right: 24, bottom: 80, background: '#fff', border: '1px solid #e2e8f0' }}
        >
          {/* ヘッダー */}
          <div className="flex items-center gap-2.5 px-4 py-3 shrink-0" style={{ background: '#1e2330' }}>
            <div className="w-7 h-7 rounded flex items-center justify-center shrink-0" style={{ background: '#2563a8' }}>
              <svg className="w-4 h-4 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
              </svg>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-white text-sm font-medium leading-none">MARKS アシスタント</p>
              <p className="text-xs mt-0.5" style={{ color: '#6b7899' }}>データについて質問できます</p>
            </div>
            {messages.length > 0 && (
              <button
                onClick={() => setMessages([])}
                className="text-xs px-2 py-1 rounded"
                style={{ color: '#6b7899' }}
              >
                クリア
              </button>
            )}
          </div>

          {/* メッセージ一覧 */}
          <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3" style={{ background: '#f8fafc' }}>
            {messages.length === 0 && (
              <div className="text-center pt-8">
                <p className="text-sm text-slate-400">ダッシュボードのデータについて<br />何でも聞いてください</p>
                <div className="mt-4 space-y-2">
                  {[
                    '今月の粗利はどうですか？',
                    '注意すべきメンバーは？',
                    '情報源のROIが高いのは？',
                  ].map(q => (
                    <button
                      key={q}
                      onClick={() => { setInput(q); inputRef.current?.focus() }}
                      className="block w-full text-left text-xs px-3 py-2 rounded-lg border border-slate-200 bg-white text-slate-600 hover:border-blue-300 hover:text-blue-700 transition-colors"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((m, i) => {
              const isLast = i === messages.length - 1
              const isStreaming = isLast && m.role === 'assistant' && streaming
              const sections = m.role === 'assistant' && !isStreaming && m.content
                ? detectSections(m.content)
                : []

              return (
                <div key={i} className={`flex flex-col ${m.role === 'user' ? 'items-end' : 'items-start'}`}>
                  <div
                    className={`max-w-[85%] px-3 py-2 rounded-xl text-sm leading-relaxed ${m.role === 'user' ? 'whitespace-pre-wrap' : ''}`}
                    style={m.role === 'user'
                      ? { background: '#2563a8', color: '#fff', borderBottomRightRadius: 4 }
                      : { background: '#fff', color: '#1e293b', border: '1px solid #e2e8f0', borderBottomLeftRadius: 4 }
                    }
                  >
                    {m.role === 'assistant' ? (
                      <ReactMarkdown
                        components={{
                          p:      ({ children }) => <p className="mb-1 last:mb-0">{children}</p>,
                          strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
                          ul:     ({ children }) => <ul className="list-disc pl-4 mb-1 space-y-0.5">{children}</ul>,
                          ol:     ({ children }) => <ol className="list-decimal pl-4 mb-1 space-y-0.5">{children}</ol>,
                          li:     ({ children }) => <li className="leading-snug">{children}</li>,
                          code:   ({ children }) => <code className="bg-slate-100 text-slate-700 rounded px-1 text-xs font-mono">{children}</code>,
                        }}
                      >
                        {m.content}
                      </ReactMarkdown>
                    ) : m.content}
                    {isStreaming && m.content === '' && (
                      <span className="inline-flex gap-1 items-center">
                        <span className="w-1.5 h-1.5 rounded-full bg-slate-300 animate-bounce" style={{ animationDelay: '0ms' }} />
                        <span className="w-1.5 h-1.5 rounded-full bg-slate-300 animate-bounce" style={{ animationDelay: '150ms' }} />
                        <span className="w-1.5 h-1.5 rounded-full bg-slate-300 animate-bounce" style={{ animationDelay: '300ms' }} />
                      </span>
                    )}
                  </div>

                  {/* 関連グラフへのジャンプボタン */}
                  {sections.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mt-1.5 max-w-[85%]">
                      {sections.map(s => (
                        <button
                          key={s.anchorId || s.path}
                          onClick={() => navigateToSection(s.path, s.anchorId)}
                          className="flex items-center gap-1 text-xs px-2.5 py-1 rounded-full border transition-colors hover:bg-blue-100"
                          style={{ borderColor: '#2563a8', color: '#2563a8', background: '#eff6ff' }}
                        >
                          <svg className="w-3 h-3 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <polyline points="15 10 20 15 15 20"/><path d="M4 4v7a4 4 0 0 0 4 4h12"/>
                          </svg>
                          {s.label}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )
            })}
            <div ref={bottomRef} />
          </div>

          {/* 入力エリア */}
          <div className="px-3 py-2.5 border-t border-slate-100 flex gap-2 items-end shrink-0">
            <textarea
              ref={inputRef}
              rows={1}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder="質問を入力… (Enter で送信)"
              disabled={streaming}
              className="flex-1 resize-none text-sm px-3 py-2 rounded-lg border border-slate-200 outline-none focus:border-blue-400 disabled:opacity-50"
              style={{ maxHeight: 96, lineHeight: '1.5' }}
            />
            <button
              onClick={send}
              disabled={!input.trim() || streaming}
              className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0 disabled:opacity-40"
              style={{ background: '#2563a8' }}
            >
              <svg className="w-4 h-4 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
              </svg>
            </button>
          </div>
        </div>
      )}
    </>
  )
}
