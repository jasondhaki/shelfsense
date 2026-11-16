import { ScanLine, Upload } from 'lucide-react'
import { useRef, useState } from 'react'
import BoundingBoxCanvas from '../components/BoundingBoxCanvas'
import VisionResult from '../components/VisionResult'
import { simClock } from '../lib/format'
import { FRAMES, useSim } from '../store/simStore'

export default function SmartCamInspector() {
  const v = useSim((s) => s.vision)
  const tick = useSim((s) => s.snapshot?.tick ?? 0)
  const selectFrame = useSim((s) => s.selectFrame)
  const selectUpload = useSim((s) => s.selectUpload)
  const scan = useSim((s) => s.scan)
  const input = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)

  const pick = (files: FileList | null) => files?.[0] && selectUpload(files[0])
  const frameLabel = FRAMES.find((f) => f.id === v.frameId)?.label ?? 'Your image'

  return (
    <section aria-label="Smart-cam inspector" className="zone flex flex-col gap-3 overflow-y-auto p-3">
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-[11px] font-medium leading-tight">CAM-04: Fresh produce aisle — Bay 2</h2>
        <span className="flex shrink-0 items-center gap-1.5 font-mono text-[11px] tabular-nums text-muted">
          <span className="h-2 w-2 rounded-full bg-crit motion-safe:animate-pulse" aria-hidden />
          REC {simClock(tick)}
        </span>
      </div>

      <BoundingBoxCanvas
        src={v.imageUrl}
        alt={`Camera frame: ${frameLabel}`}
        detections={v.result?.extraction.detections ?? []}
        scanning={v.scanning}
      />

      <div className="grid grid-cols-4 gap-1.5" role="group" aria-label="Camera frames">
        {FRAMES.map((f) => (
          <button
            key={f.id}
            type="button"
            aria-pressed={v.frameId === f.id}
            aria-label={`Frame ${f.id.slice(-1)}: ${f.label}`}
            onClick={() => selectFrame(f.id)}
            className={`overflow-hidden rounded-md border text-left ${v.frameId === f.id ? 'border-accent' : 'border-line hover:border-accent/60'}`}
          >
            <img src={f.src} alt="" className="aspect-[4/3] w-full object-cover" />
            <span className="block truncate px-1 py-0.5 text-[10px] text-muted">{f.label}</span>
          </button>
        ))}
        <button
          type="button"
          aria-label="Upload your own image (JPG or PNG, up to 5 MB)"
          onClick={() => input.current?.click()}
          onDragOver={(e) => {
            e.preventDefault()
            setDragging(true)
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault()
            setDragging(false)
            pick(e.dataTransfer.files)
          }}
          className={`flex flex-col items-center justify-center gap-1 rounded-md border border-dashed text-[10px] text-muted ${
            v.frameId === 'custom' ? 'border-accent text-accent' : dragging ? 'border-accent' : 'border-line hover:border-accent/60'
          }`}
        >
          <Upload size={14} aria-hidden />
          Upload
        </button>
        <input
          ref={input}
          type="file"
          accept="image/jpeg,image/png"
          className="sr-only"
          tabIndex={-1}
          onChange={(e) => {
            pick(e.target.files)
            e.target.value = ''
          }}
        />
      </div>

      <button type="button" className="btn justify-center py-2" disabled={v.scanning} onClick={() => scan()}>
        <ScanLine size={14} aria-hidden />
        {v.scanning ? 'Scanning…' : 'Run vision scan'}
      </button>

      {v.error && (
        <p role="alert" className="text-xs text-crit">
          {v.error}
        </p>
      )}
      {v.result ? (
        <VisionResult r={v.result} />
      ) : (
        !v.scanning &&
        !v.error && (
          <p className="text-xs text-muted">
            Scan a frame to grade freshness. A damaged batch gets a shorter shelf life, and the
            shelf label reprices on the next hour.
          </p>
        )
      )}
    </section>
  )
}
