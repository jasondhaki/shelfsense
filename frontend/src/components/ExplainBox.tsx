import { Sparkles } from 'lucide-react'
import { useState } from 'react'
import { api } from '../lib/api'
import { useT } from '../lib/i18n'
import type { Explanation, LogEntry } from '../types/contracts'

/** Plain-language, source-cited explanation of one log line (POST /api/explain). */
export default function ExplainBox({ e }: { e: LogEntry }) {
  const t = useT()
  const [res, setRes] = useState<Explanation | null>(null)
  const [busy, setBusy] = useState(false)
  const [failed, setFailed] = useState(false)

  if (!res) {
    const go = async () => {
      setBusy(true)
      setFailed(false)
      try {
        setRes(await api.explain({ agent: e.agent, message: e.message, data: e.data }))
      } catch {
        setFailed(true)
      } finally {
        setBusy(false)
      }
    }
    return (
      <div className="mt-1 flex items-center gap-2">
        <button type="button" className="btn text-[11px]" disabled={busy} onClick={go}>
          <Sparkles size={12} aria-hidden /> {busy ? t('Explaining…') : t('Explain in plain words')}
        </button>
        {failed && <span className="text-[11px] text-warn">{t('Couldn’t get an explanation.')}</span>}
      </div>
    )
  }
  return (
    <div className="mt-1 rounded bg-bg p-2 font-sans text-[12px] text-text" aria-live="polite">
      <p>{res.text}</p>
      <p className="mt-1 text-[10px] text-muted">
        {res.mode === 'llm'
          ? t('Written by {model}; every number is checked against the log and sources.', {
              model: `${res.provider ?? ''} ${res.model ?? ''}`.trim(),
            })
          : t('Template text: no language model is configured, or it did not answer.')}
        {res.guardrail && ` ${t('The model’s answer was rejected: it used a number that is not in the log or sources.')}`}
      </p>
      {res.citations.length > 0 && (
        <ul className="mt-1 list-disc pl-4 text-[10px] text-muted">
          {res.citations.map((c) => (
            <li key={c.chunk_id}>
              {c.url.startsWith('http') ? (
                <a href={c.url} target="_blank" rel="noreferrer" className="underline">
                  {c.source} — {c.title}
                </a>
              ) : (
                `${c.source} — ${c.title}`
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
