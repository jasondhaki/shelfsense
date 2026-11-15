import { CloudRain, FastForward, Pause, Play, RotateCcw, StepForward } from 'lucide-react'
import { useState } from 'react'
import ColdChainPopover from '../components/ColdChainPopover'
import KpiCard from '../components/KpiCard'
import { CYCLE_TICKS, simClock, usd } from '../lib/format'
import { useSim } from '../store/simStore'

const DEBUG = new URLSearchParams(location.search).has('debug')

export default function TelemetryBar() {
  const snap = useSim((s) => s.snapshot)
  const control = useSim((s) => s.control)
  const triggerEvent = useSim((s) => s.triggerEvent)
  const [confirmReset, setConfirmReset] = useState(false)

  if (!snap) return <header className="zone h-[76px]" aria-busy />

  const finished = snap.status === 'finished'
  const playing = snap.status === 'playing'
  const storm = snap.active_events.find((e) => e.type === 'rainstorm')
  const stormLeft = storm?.active_until_tick != null ? storm.active_until_tick - snap.tick : 0
  const coldPending = snap.active_events.some((e) => e.type === 'cold_chain_delay')
  const w = snap.weather
  const k = snap.kpis

  return (
    <header className="zone flex flex-wrap items-center gap-x-5 gap-y-3 px-4 py-3">
      <div className="mr-1">
        <div className="text-lg font-bold leading-tight tracking-tight">ShelfSense</div>
        <div className="text-[11px] text-muted">a FoodSphere AI system</div>
      </div>

      <div className="flex items-center gap-1" role="group" aria-label="Playback">
        <button
          type="button"
          className={`btn-icon ${playing && snap.speed === 1 ? 'btn-on' : ''}`}
          aria-label="Play at 1 simulated hour per second"
          disabled={finished}
          onClick={() => control('play')}
        >
          <Play size={16} aria-hidden />
        </button>
        <button
          type="button"
          className={`btn-icon ${playing && snap.speed > 1 ? 'btn-on' : ''}`}
          aria-label="Fast-forward"
          disabled={finished}
          onClick={() => control('fast_forward')}
        >
          <FastForward size={16} aria-hidden />
        </button>
        <button
          type="button"
          className="btn-icon"
          aria-label="Pause"
          disabled={!playing}
          onClick={() => control('pause')}
        >
          <Pause size={16} aria-hidden />
        </button>
        {DEBUG && (
          <button
            type="button"
            className="btn-icon"
            aria-label="Step one hour"
            disabled={finished}
            onClick={() => control('step')}
          >
            <StepForward size={16} aria-hidden />
          </button>
        )}
        {confirmReset ? (
          <span className="ml-1 flex items-center gap-1 text-xs" role="alertdialog" aria-label="Confirm reset">
            Reset to Day 1? Current run will be lost.
            <button
              type="button"
              className="btn"
              autoFocus
              onClick={() => {
                setConfirmReset(false)
                void control('reset')
              }}
            >
              Reset
            </button>
            <button type="button" className="btn" onClick={() => setConfirmReset(false)}>
              Keep run
            </button>
          </span>
        ) : (
          <button
            type="button"
            className="btn-icon"
            aria-label="Reset to Day 1"
            onClick={() => setConfirmReset(true)}
          >
            <RotateCcw size={16} aria-hidden />
          </button>
        )}
      </div>

      <div className="w-36">
        <div className="flex items-baseline justify-between font-mono tabular-nums">
          <span className="text-base">{simClock(snap.tick)}</span>
          <span className="text-[11px] text-muted">
            {snap.tick}/{CYCLE_TICKS}
          </span>
        </div>
        <div
          className="mt-1 h-1.5 overflow-hidden rounded-full bg-line"
          role="progressbar"
          aria-label="Simulation progress"
          aria-valuemin={0}
          aria-valuemax={CYCLE_TICKS}
          aria-valuenow={snap.tick}
        >
          <div className="h-full bg-accent" style={{ width: `${(snap.tick / CYCLE_TICKS) * 100}%` }} />
        </div>
      </div>

      <div className="text-xs leading-snug" aria-label="Weather">
        <div className="font-mono tabular-nums">
          {w.temperature_f != null ? `${w.temperature_f}°F` : '—'} · RH{' '}
          {w.relative_humidity_pct.toFixed(0)}% · rain {w.precip_probability_pct ?? 0}%
        </div>
        <div className="text-muted">
          {w.location} ·{' '}
          <span className={w.source === 'live' ? 'text-ok' : ''}>
            NOAA {w.source === 'live' ? 'live' : 'snapshot'}
          </span>
        </div>
      </div>

      <div className="flex items-center gap-2" role="group" aria-label="Disruptions">
        <button
          type="button"
          className="btn"
          disabled={finished || !!storm}
          onClick={() => triggerEvent('rainstorm')}
        >
          <CloudRain size={14} aria-hidden />
          {storm ? `Storm: ${stormLeft} h left` : 'Rainstorm'}
        </button>
        <ColdChainPopover
          skus={snap.esl}
          pending={coldPending}
          disabled={finished}
          onTrigger={(skus, immediate) => triggerEvent('cold_chain_delay', { skus, immediate })}
        />
      </div>

      <div className="ml-auto flex gap-2">
        <KpiCard
          label="Waste reduction vs baseline"
          value={k.waste_reduction_pct}
          format={(n) => `${n.toFixed(1)}%`}
          target={30}
        />
        <KpiCard
          label="Food diverted"
          value={k.food_diverted_kg}
          format={(n) => `${n.toFixed(1)} kg`}
          sub={`${k.co2e_avoided_kg.toFixed(0)} kg CO₂e avoided`}
        />
        <KpiCard
          label="Net margin recovered"
          value={k.net_margin_recovered_usd}
          format={usd}
          sub="vs baseline store"
        />
      </div>
    </header>
  )
}
