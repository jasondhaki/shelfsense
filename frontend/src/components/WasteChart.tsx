import { useState } from 'react'
import {
  CartesianGrid,
  LabelList,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { simClock } from '../lib/format'
import type { ChartPoint } from '../types/contracts'

// Checked with the dataviz validator on #FFFFFF: normal-vision ΔE 18.4, CVD ΔE 14.3, contrast ≥ 3:1.
// The baseline is a deliberately recessive grey (low chroma), always dashed and labelled.
const A = 'rgb(var(--c-chart-a))'
const B = 'rgb(var(--c-accent))'
const GRID = 'rgb(var(--c-grid))'
const MUTED = 'rgb(var(--c-muted))'

interface TipProps {
  active?: boolean
  label?: number
  payload?: { dataKey?: string | number; value?: number }[]
}

function Tip({ active, label, payload }: TipProps) {
  if (!active || !payload?.length || label === undefined) return null
  const v = (k: string) => payload.find((p) => p.dataKey === k)?.value ?? 0
  return (
    <div className="rounded-md border border-line bg-panel-2 px-2.5 py-1.5 font-mono text-[11px] tabular-nums shadow-lg">
      <div className="mb-0.5 text-muted">{simClock(label)}</div>
      <div className="flex items-center gap-2 text-text">
        <svg width="14" height="2" aria-hidden><line x1="0" y1="1" x2="14" y2="1" stroke={A} strokeWidth="2" strokeDasharray="4 3" /></svg>
        Baseline store {v('waste_kg_a').toFixed(1)} kg
      </div>
      <div className="flex items-center gap-2 text-text">
        <svg width="14" height="2" aria-hidden><line x1="0" y1="1" x2="14" y2="1" stroke={B} strokeWidth="2" /></svg>
        ShelfSense store {v('waste_kg_b').toFixed(1)} kg
      </div>
    </div>
  )
}

/** Cumulative food waste, both stores — the headline comparison over the week. */
export default function WasteChart({ data }: { data: ChartPoint[] }) {
  const [asTable, setAsTable] = useState(false)
  const last = data.length - 1
  const daily = data.filter((p) => p.tick % 24 === 23 || p.tick === data[last]?.tick)

  return (
    <figure className="flex h-full min-h-0 flex-col">
      <figcaption className="flex items-center justify-between px-1 pb-1">
        <span className="text-xs font-medium">Food wasted so far</span>
        <span className="flex items-center gap-3 text-[11px] text-muted">
          <span className="flex items-center gap-1.5">
            <svg width="16" height="2" aria-hidden><line x1="0" y1="1" x2="16" y2="1" stroke={A} strokeWidth="2" strokeDasharray="4 3" /></svg>
            Baseline
          </span>
          <span className="flex items-center gap-1.5">
            <svg width="16" height="2" aria-hidden><line x1="0" y1="1" x2="16" y2="1" stroke={B} strokeWidth="2" /></svg>
            ShelfSense
          </span>
          <button type="button" className="underline-offset-2 hover:underline" onClick={() => setAsTable((t) => !t)}>
            {asTable ? 'Show chart' : 'Show table'}
          </button>
        </span>
      </figcaption>
      {asTable ? (
        <div className="min-h-0 flex-1 overflow-auto">
          <table className="w-full font-mono text-[11px] tabular-nums">
            <thead className="text-muted">
              <tr>
                <th className="text-left font-normal">Time</th>
                <th className="text-right font-normal">Baseline kg</th>
                <th className="text-right font-normal">ShelfSense kg</th>
              </tr>
            </thead>
            <tbody>
              {daily.map((p) => (
                <tr key={p.tick}>
                  <td>{simClock(p.tick)}</td>
                  <td className="text-right">{p.waste_kg_a.toFixed(1)}</td>
                  <td className="text-right">{p.waste_kg_b.toFixed(1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : data.length === 0 ? (
        <p className="grid flex-1 place-items-center text-xs text-muted">Press play to plot the week.</p>
      ) : (
        <div className="min-h-0 flex-1" role="img" aria-label="Line chart of cumulative food waste in kilograms for both stores">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 14, right: 104, bottom: 0, left: 0 }}>
              <CartesianGrid stroke={GRID} vertical={false} />
              <XAxis
                dataKey="tick"
                type="number"
                domain={[0, 167]}
                ticks={[0, 24, 48, 72, 96, 120, 144]}
                tickFormatter={(t: number) => `D${t / 24 + 1}`}
                stroke={MUTED}
                tick={{ fontSize: 10 }}
                tickLine={false}
                axisLine={{ stroke: GRID }}
              />
              <YAxis
                stroke={MUTED}
                tick={{ fontSize: 10 }}
                tickLine={false}
                axisLine={false}
                width={52}
                tickFormatter={(v: number) => `${v} kg`}
              />
              <Tooltip content={<Tip />} cursor={{ stroke: MUTED, strokeWidth: 1 }} isAnimationActive={false} />
              <Line type="monotone" dataKey="waste_kg_a" stroke={A} strokeWidth={2} strokeDasharray="5 4" dot={false} isAnimationActive={false}>
                <LabelList dataKey="waste_kg_a" content={(p) => endLabel(p, last, 'Baseline', data[last]?.waste_kg_b ?? 0)} />
              </Line>
              <Line type="monotone" dataKey="waste_kg_b" stroke={B} strokeWidth={2} dot={false} isAnimationActive={false}>
                <LabelList dataKey="waste_kg_b" content={(p) => endLabel(p, last, 'ShelfSense', data[last]?.waste_kg_a ?? 0)} />
              </Line>
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </figure>
  )
}

/** Direct label at the line end only — never a number on every point. Text uses text tokens. */
function endLabel(
  p: { index?: number; x?: number | string; y?: number | string; value?: unknown },
  last: number,
  name: string,
  other: number,
) {
  if (p.index !== last || typeof p.x !== 'number' || typeof p.y !== 'number') return null
  // Both labels sit above their line ends; when the lines are close the higher one is lifted
  // further so the two never overlap (and neither drops into the x-axis).
  const v = Number(p.value)
  const close = Math.abs(v - other) <= 0.08 * Math.max(v, other, 1)
  const higher = v > other || (v === other && name === 'Baseline')
  const dy = close && higher ? -17 : -5
  return (
    <text x={p.x + 6} y={p.y} dy={dy} fontSize={10} fill="rgb(var(--c-text))" fontFamily="JetBrains Mono, monospace">
      {name} {v.toFixed(v < 10 ? 1 : 0)} kg
    </text>
  )
}
