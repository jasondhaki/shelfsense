import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { atRisk, freshness } from '../lib/insights'
import { useT } from '../lib/i18n'
import type { EslView } from '../types/contracts'

const BUCKETS = [
  { key: 'Fresh', color: 'rgb(var(--c-accent))' },
  { key: 'Ageing', color: 'rgb(var(--c-warn))' },
  { key: 'At risk', color: 'rgb(var(--c-crit))' },
] as const

/** Units on the shelf split by freshness left (oldest batch of each line). */
export default function ShelfHealthCard({ rows }: { rows: EslView[] }) {
  const t = useT()
  const units = [0, 0, 0]
  for (const e of rows) {
    if (!e.on_hand) continue
    units[atRisk(e) ? 2 : freshness(e) < 0.5 ? 1 : 0] += e.on_hand
  }
  const total = units[0] + units[1] + units[2]
  const data = BUCKETS.map((b, i) => ({ name: t(b.key), value: units[i], color: b.color }))

  return (
    <section aria-labelledby="sh-title" className="zone p-3">
      <h2 id="sh-title" className="h-card">
        {t('Shelf health')}
      </h2>
      <p className="mt-0.5 text-xs text-muted">{t('Units on shelf by freshness left.')}</p>
      <div className="mt-2 flex items-center gap-4">
        <div className="relative h-[130px] w-[130px] shrink-0">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={data} dataKey="value" innerRadius="68%" outerRadius="100%" paddingAngle={total ? 2 : 0} stroke="none" isAnimationActive={false}>
                {data.map((d) => (
                  <Cell key={d.name} fill={d.color} />
                ))}
              </Pie>
              <Tooltip formatter={(v) => t('{n} units', { n: String(v) })} />
            </PieChart>
          </ResponsiveContainer>
          <div className="pointer-events-none absolute inset-0 grid place-items-center text-center">
            <div>
              <div className="text-xl font-extrabold leading-none">{total}</div>
              <div className="text-[11px] text-muted">{t('on shelf')}</div>
            </div>
          </div>
        </div>
        <ul className="min-w-0 flex-1 space-y-2 text-sm">
          {data.map((d) => (
            <li key={d.name} className="flex items-center gap-2">
              <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: d.color }} aria-hidden />
              <span className="flex-1 truncate">{d.name}</span>
              <span className="font-bold">{d.value}</span>
              <span className="w-10 text-right text-xs text-muted">{total ? `${Math.round((d.value / total) * 100)}%` : '—'}</span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}
