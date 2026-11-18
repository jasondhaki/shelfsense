import { useState } from 'react'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { simClock } from '../lib/format'
import { useMedia } from '../lib/useMedia'
import { useT } from '../lib/i18n'
import { shortName } from '../lib/insights'
import type { ChartPoint, EslView } from '../types/contracts'

// Validated with the dataviz script on #FFFFFF: green/violet pass all checks; the baseline is a
// deliberately recessive grey, always dashed and labelled (secondary encoding).
const GREEN = 'rgb(var(--c-accent))'
const VIOLET = 'rgb(var(--c-agent-vision))'
const GREY = 'rgb(var(--c-chart-a))'
const GRID = 'rgb(var(--c-grid))'
const AXIS = { fontSize: 11, fill: 'rgb(var(--c-muted))' }

const tipStyle = {
  borderRadius: 12,
  border: '1px solid rgb(var(--c-line))',
  background: 'rgb(var(--c-panel))',
  color: 'rgb(var(--c-text))',
  boxShadow: '0 8px 24px -12px rgba(15,42,31,0.25)',
  fontSize: 12,
}

type Tab = 'demand' | 'waste'

export default function DemandWasteCard({ esl, chart }: { esl: EslView[]; chart: ChartPoint[] }) {
  const [tab, setTab] = useState<Tab>('demand')
  const narrow = useMedia('(max-width: 639px)')
  const t = useT()
  const demand = esl.map((e) => ({
    name: shortName(e.name).split(' ').slice(-1)[0],
    full: e.name,
    'On shelf': e.on_hand,
    'Next 24 h demand': Math.round(e.forecast_24h),
  }))
  const waste = chart
    .filter((_, i) => i % 2 === 0 || i === chart.length - 1)
    .map((p) => ({ tick: p.tick, Baseline: +p.waste_kg_a.toFixed(1), ShelfSense: +p.waste_kg_b.toFixed(1) }))

  return (
    <section aria-labelledby="dw-title" className="zone flex flex-col p-4">
      <h2 id="dw-title" className="h-card">
        {t('Demand & waste analytics')}
      </h2>
      <div role="tablist" aria-label={t('Chart')} className="mt-2 flex gap-4 border-b border-line text-sm">
        {(
          [
            ['demand', 'Demand forecast'],
            ['waste', 'Food waste trend'],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={tab === id}
            onClick={() => setTab(id)}
            className={`-mb-px border-b-2 pb-1.5 font-semibold ${tab === id ? 'border-accent text-accent' : 'border-transparent text-muted hover:text-text'}`}
          >
            {t(label)}
          </button>
        ))}
      </div>
      <div className="mt-3 h-[240px]" role="tabpanel">
        {tab === 'demand' ? (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={demand} barGap={2} margin={{ top: 4, right: 4, left: -18, bottom: 0 }}>
              <CartesianGrid stroke={GRID} vertical={false} />
              <XAxis
                dataKey="name"
                tick={narrow ? { ...AXIS, fontSize: 10 } : AXIS}
                tickLine={false}
                axisLine={false}
                interval={0}
                angle={narrow ? -40 : 0}
                textAnchor={narrow ? 'end' : 'middle'}
                height={narrow ? 52 : 30}
              />
              <YAxis tick={AXIS} tickLine={false} axisLine={false} allowDecimals={false} />
              <Tooltip
                contentStyle={tipStyle}
                cursor={{ fill: 'rgb(var(--c-accent) / 0.06)' }}
                labelFormatter={(_, p) => (p?.[0]?.payload as { full?: string } | undefined)?.full ?? ''}
              />
              <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 12 }} />
              <Bar dataKey="On shelf" name={t('On shelf')} fill={GREEN} radius={[4, 4, 0, 0]} maxBarSize={18} />
              <Bar dataKey="Next 24 h demand" name={t('Next 24 h demand')} fill={VIOLET} radius={[4, 4, 0, 0]} maxBarSize={18} />
            </BarChart>
          </ResponsiveContainer>
        ) : waste.length < 2 ? (
          <p className="grid h-full place-items-center text-sm text-muted">{t('Press play — the trend fills in as the week runs.')}</p>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={waste} margin={{ top: 4, right: 4, left: -18, bottom: 0 }}>
              <defs>
                <linearGradient id="dw-b" x1="0" x2="0" y1="0" y2="1">
                  <stop offset="0" stopColor={GREEN} stopOpacity={0.3} />
                  <stop offset="1" stopColor={GREEN} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke={GRID} vertical={false} />
              <XAxis
                dataKey="tick"
                type="number"
                domain={[0, 167]}
                ticks={[0, 24, 48, 72, 96, 120, 144]}
                tickFormatter={(x: number) => t('Day {n}', { n: Math.floor(x / 24) + 1 })}
                tick={AXIS}
                tickLine={false}
                axisLine={false}
              />
              <YAxis tick={AXIS} tickLine={false} axisLine={false} unit=" kg" width={58} />
              <Tooltip contentStyle={tipStyle} labelFormatter={(t) => simClock(Number(t))} formatter={(v) => `${String(v)} kg`} />
              <Legend iconType="plainline" wrapperStyle={{ fontSize: 12 }} />
              <Area type="monotone" dataKey="Baseline" name={t('Baseline')} stroke={GREY} strokeWidth={2} strokeDasharray="5 4" fill="none" isAnimationActive={false} />
              <Area type="monotone" dataKey="ShelfSense" name="ShelfSense" stroke={GREEN} strokeWidth={2} fill="url(#dw-b)" isAnimationActive={false} />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
      <p className="mt-1 text-[11px] text-muted">
        {tab === 'demand'
          ? t('Expected sales over the next 24 simulated hours: day-of-week and hourly pattern (Favorita), foot traffic and the current price.')
          : t('Cumulative food wasted this week, same shoppers in both stores.')}
      </p>
    </section>
  )
}
