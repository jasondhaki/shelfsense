import { SEVERITY } from '../lib/severity'
import type { Detection } from '../types/contracts'

const words = (s: string) => s.replace(/_/g, ' ')

interface Props {
  src: string
  alt: string
  detections: Detection[]
  scanning: boolean
}

/** The camera frame with detection boxes. Boxes arrive as [ymin, xmin, ymax, xmax] on a 0–1000
 *  grid, so they map straight to percentages of the rendered image — no pixel maths needed. */
export default function BoundingBoxCanvas({ src, alt, detections, scanning }: Props) {
  return (
    <div className="relative overflow-hidden rounded-md border border-line bg-bg">
      <img src={src} alt={alt} className="block h-auto w-full" />
      {detections.map((d, i) => {
        const [ymin, xmin, ymax, xmax] = d.box_2d
        const s = SEVERITY[d.severity]
        const top = ymin < 120 // keep the chip inside the frame when a box touches the top
        return (
          <div
            key={i}
            className={`absolute rounded-sm border-2 ${s.border}`}
            style={{
              top: `${ymin / 10}%`,
              left: `${xmin / 10}%`,
              height: `${(ymax - ymin) / 10}%`,
              width: `${(xmax - xmin) / 10}%`,
            }}
          >
            <span
              className={`absolute left-0 flex max-w-full items-center gap-1 truncate rounded-sm px-1 py-px text-[10px] font-medium ${s.chip} ${top ? 'top-0' : '-top-[18px]'}`}
            >
              <s.Icon size={10} aria-hidden />
              {d.defects.length ? words(d.defects[0]) : s.label} · {Math.round(d.confidence * 100)}%
            </span>
          </div>
        )
      })}
      {scanning && (
        <div className="pointer-events-none absolute inset-0" aria-hidden>
          <div className="scanline absolute inset-x-0 h-8 bg-gradient-to-b from-transparent via-accent/30 to-transparent" />
        </div>
      )}
    </div>
  )
}
