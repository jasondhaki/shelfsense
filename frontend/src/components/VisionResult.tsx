import { ArrowDown, BookOpen } from 'lucide-react'
import type { VisionScanResult } from '../types/contracts'
import { simClock } from '../lib/format'
import { useT } from '../lib/i18n'

const words = (s: string) => s.replace(/_/g, ' ')

function QualityGauge({ q }: { q: number | null }) {
  const t = useT()
  if (q === null) return <span className="text-xs text-muted">{t('No food recognised')}</span>
  const tone = q >= 8 ? 'bg-ok' : q >= 5 ? 'bg-warn' : 'bg-crit'
  return (
    <div className="flex items-center gap-2">
      <div
        className="h-2 flex-1 overflow-hidden rounded-full bg-line"
        role="meter"
        aria-label={t('Visual quality score')}
        aria-valuemin={1}
        aria-valuemax={10}
        aria-valuenow={q}
      >
        <div className={`h-full ${tone}`} style={{ width: `${(q / 10) * 100}%` }} />
      </div>
      <span className="font-mono text-sm tabular-nums">{q.toFixed(1)}/10</span>
    </div>
  )
}

export default function VisionResult({ r }: { r: VisionScanResult }) {
  const x = r.extraction
  const t = useT()
  const dropped = r.rsl_before_hours !== null && r.rsl_after_hours !== null && r.rsl_after_hours < r.rsl_before_hours - 0.05
  return (
    <div className="space-y-3 text-xs">
      <div className="flex items-center justify-between">
        <span className="text-muted">{t('Visual quality')}</span>
        <span
          className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${r.mode === 'live' ? 'bg-agent-vision/20 text-agent-vision' : 'bg-line text-muted'}`}
        >
          {t(r.mode === 'live' ? 'live Gemini' : 'cached result')}
        </span>
      </div>
      <QualityGauge q={x.visual_quality_score} />

      <div className="flex flex-wrap gap-1">
        {x.defects_detected.length === 0 ? (
          <span className="rounded-sm bg-ok/15 px-1.5 py-0.5 text-ok">{t('No defects seen')}</span>
        ) : (
          x.defects_detected.map((d) => (
            <span key={d} className="rounded-sm bg-panel-2 px-1.5 py-0.5 text-text">
              {words(d)}
            </span>
          ))
        )}
        <span className="rounded-sm bg-panel-2 px-1.5 py-0.5 font-mono tabular-nums text-muted">
          {t(x.estimated_unit_count === 1 ? '{n} unit' : '{n} units', { n: x.estimated_unit_count })}
        </span>
      </div>
      <p className="text-muted">{x.rationale}</p>

      {r.target_sku && r.rsl_before_hours !== null && (
        <div className="rounded-md border border-line bg-panel-2 p-2.5">
          <div className="mb-1.5 font-mono text-[11px] text-muted">
            {r.target_sku} · {t('oldest batch')} · α_vision {r.alpha_vision.toFixed(2)}
          </div>
          <div className="flex items-center justify-between font-mono tabular-nums">
            <span className="text-muted">{t('Printed label')}</span>
            <span>{r.printed_remaining_hours?.toFixed(0)} h</span>
          </div>
          <div className="flex items-center justify-between font-mono tabular-nums">
            <span className="text-muted">{t('Shelf life believed')}</span>
            <span>{r.rsl_before_hours.toFixed(1)} h</span>
          </div>
          <div className="flex items-center justify-between font-mono text-sm font-semibold tabular-nums">
            <span className="font-sans text-xs font-normal text-muted">{t('Recalibrated')}</span>
            <span className={`flex items-center gap-1 ${dropped ? 'text-crit' : 'text-ok'}`}>
              {dropped && <ArrowDown size={13} aria-label={t('dropped')} />}
              {r.rsl_after_hours?.toFixed(1)} h
            </span>
          </div>
          {r.applied_at_tick !== null && (
            <div className="mt-1 text-[11px] text-muted">
              {t('Applied to pricing at {at}', { at: simClock(r.applied_at_tick) })}
            </div>
          )}
        </div>
      )}

      {r.foodkeeper_citation && (
        <div className="flex gap-1.5 text-[11px] text-muted">
          <BookOpen size={12} className="mt-0.5 shrink-0" aria-hidden />
          <span>
            {t('Source:')} {r.foodkeeper_citation.source} — {r.foodkeeper_citation.title}
            {r.foodkeeper_citation.score !== null && (
              <span className="font-mono tabular-nums">
                {' '}
                ({r.foodkeeper_citation.mode} {r.foodkeeper_citation.score.toFixed(2)})
              </span>
            )}
            <span className="mt-0.5 block text-muted/80">“{r.foodkeeper_citation.text.slice(0, 120)}”</span>
          </span>
        </div>
      )}
      {r.note && <p className="text-[11px] text-warn">{r.note}</p>}
    </div>
  )
}
