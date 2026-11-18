import { ArrowRight, ScanLine } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { SEVERITY } from '../lib/severity'
import { useT } from '../lib/i18n'
import { useSim } from '../store/simStore'

/** Where an image drawn with object-fit: cover lands inside its box, so 0–1000 detection
 *  coordinates can be mapped onto the cropped photo. */
function useCoverRect() {
  const box = useRef<HTMLDivElement>(null)
  const [nat, setNat] = useState<{ w: number; h: number } | null>(null)
  const [size, setSize] = useState({ w: 0, h: 0 })
  useEffect(() => {
    const el = box.current
    if (!el) return
    const ro = new ResizeObserver(([e]) => setSize({ w: e.contentRect.width, h: e.contentRect.height }))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])
  let rect = { x: 0, y: 0, w: size.w, h: size.h }
  if (nat && size.w && size.h) {
    const s = Math.max(size.w / nat.w, size.h / nat.h)
    const w = nat.w * s
    const h = nat.h * s
    rect = { x: (size.w - w) / 2, y: (size.h - h) / 2, w, h }
  }
  return { box, rect, onLoad: (img: HTMLImageElement) => setNat({ w: img.naturalWidth, h: img.naturalHeight }) }
}

export default function FreshnessHero() {
  const v = useSim((s) => s.vision)
  const esl = useSim((s) => s.snapshot?.esl)
  const scan = useSim((s) => s.scan)
  const setPage = useSim((s) => s.setPage)
  const { box, rect, onLoad } = useCoverRect()
  const t = useT()

  const r = v.result
  const det = r?.extraction.detections ?? []
  const target = esl?.find((e) => e.sku_id === r?.target_sku)
  const q = r?.extraction.visual_quality_score ?? null
  const worst = det.find((d) => d.severity === 'clearance_required') ?? det.find((d) => d.severity === 'accelerated_ripening') ?? det[0]

  return (
    <section aria-label={t('Freshness scanner')} className="zone relative min-h-[190px] overflow-hidden max-sm:border-accent/50 sm:min-h-[260px]">
      <div ref={box} className="absolute inset-y-0 right-0 w-[62%] sm:inset-x-0 sm:w-auto">
        <img
          src={v.imageUrl}
          alt={t('Shelf camera view of the fresh produce aisle')}
          onLoad={(e) => onLoad(e.currentTarget)}
          className="h-full w-full object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-r from-panel via-panel/30 to-transparent sm:from-forest-950/35 sm:via-transparent" aria-hidden />
        {det.map((d, i) => {
          const [ymin, xmin, ymax, xmax] = d.box_2d
          const s = SEVERITY[d.severity]
          return (
            <div
              key={i}
              className={`absolute rounded-md border-2 ${s.border}`}
              style={{
                left: rect.x + (xmin / 1000) * rect.w,
                top: rect.y + (ymin / 1000) * rect.h,
                width: ((xmax - xmin) / 1000) * rect.w,
                height: ((ymax - ymin) / 1000) * rect.h,
              }}
              aria-hidden
            />
          )
        })}
        {v.scanning && (
          <div className="pointer-events-none absolute inset-0" aria-hidden>
            <div className="scanline absolute inset-x-0 h-10 bg-gradient-to-b from-transparent via-white/50 to-transparent" />
          </div>
        )}
      </div>

      <div className="relative z-10 w-[74%] p-4 sm:absolute sm:right-4 sm:top-4 sm:w-auto sm:max-w-[300px] sm:rounded-xl sm:border sm:border-white/60 sm:bg-white/85 sm:p-3 sm:shadow-card sm:backdrop-blur-md sm:dark:border-white/10 sm:dark:bg-panel/85">
        <div className="flex items-center gap-1.5 text-sm font-bold">
          {t('Freshness scanner')}
          <span className="font-semibold text-muted">|</span>
          <span className={r ? 'text-accent' : 'text-muted'}>{t(v.scanning ? 'Scanning…' : r ? 'Active' : 'Ready')}</span>
          <span className={`h-2 w-2 rounded-full ${r || v.scanning ? 'bg-ok' : 'bg-baseline'}`} aria-hidden />
        </div>
        {r ? (
          <div className="mt-1 text-sm">
            <div>
              <span className="font-bold">{target?.name ?? r.extraction.primary_sku_label}</span>
              {q !== null && <> · {t('Quality')} {q.toFixed(1)}/10</>}
            </div>
            <div className="text-muted">
              {r.rsl_after_hours !== null
                ? t('Shelf life: {h} h', { h: r.rsl_after_hours.toFixed(0) }) +
                  (r.rsl_before_hours !== null && r.rsl_after_hours < r.rsl_before_hours - 0.05
                    ? ` ${t('(was {h} h)', { h: r.rsl_before_hours.toFixed(0) })}`
                    : '')
                : target
                  ? t('Not on the shelf right now')
                  : t('No matching shelf item')}
              {worst && worst.severity !== 'optimal' && <> · {t(SEVERITY[worst.severity].label).toLowerCase()}</>}
            </div>
          </div>
        ) : (
          <p className="mt-1 line-clamp-2 text-sm text-muted sm:line-clamp-none">{t('Grade this shelf with the vision agent. Damage shortens shelf life and reprices the label.')}</p>
        )}
        <div className="mt-2 flex items-center gap-3">
          <button type="button" className="btn-primary" disabled={v.scanning} onClick={() => scan()}>
            <ScanLine size={14} aria-hidden />
            {t(r ? 'Scan again' : 'Scan shelf')}
          </button>
          <button type="button" className="link" onClick={() => setPage('agents')}>
            {t('Open scanner')} <ArrowRight size={13} aria-hidden />
          </button>
        </div>
        {v.error && (
          <p role="alert" className="mt-1 text-xs text-crit">
            {v.error}
          </p>
        )}
      </div>
    </section>
  )
}
