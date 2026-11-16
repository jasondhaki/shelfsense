import { CloudRain, FastForward, Pause, Play, RotateCcw, StepForward } from 'lucide-react'
import { useState } from 'react'
import ColdChainPopover from '../components/ColdChainPopover'
import { CYCLE_TICKS, simClock } from '../lib/format'
import { useSim } from '../store/simStore'

const DEBUG = new URLSearchParams(location.search).has('debug')

/** Week playback and disruption triggers — the demo's controls, on every tab. */
export default function SimBar() {
  const snap = useSim((s) => s.snapshot)
  const control = useSim((s) => s.control)
  const triggerEvent = useSim((s) => s.triggerEvent)
  const [confirmReset, setConfirmReset] = useState(false)

  if (!snap) return <div className="zone h-[58px]" aria-busy />

  const finished = snap.status === 'finished'
  const playing = snap.status === 'playing'
  const storm = snap.active_events.find((e) => e.type === 'rainstorm')
  const stormLeft = storm?.active_until_tick != null ? storm.active_until_tick - snap.tick : 0
  const coldPending = snap.active_events.some((e) => e.type === 'cold_chain_delay')

  return (
    <section aria-label="Simulation controls" className="zone flex flex-wrap items-center gap-x-4 gap-y-2 px-4 py-2.5">
      <div className="flex items-center gap-1.5" role="group" aria-label="Playback">
        <button
          type="button"
          className={`btn-icon ${playing && snap.speed === 1 ? 'btn-on' : ''}`}
          aria-label="Play at 1 simulated hour per second"
          disabled={finished}
          onClick={() => control('play')}
        >
          <Play size={15} aria-hidden />
        </button>
        <button
          type="button"
          className={`btn-icon ${playing && snap.speed > 1 ? 'btn-on' : ''}`}
          aria-label="Fast-forward"
          disabled={finished}
          onClick={() => control('fast_forward')}
        >
          <FastForward size={15} aria-hidden />
        </button>
        <button type="button" className="btn-icon" aria-label="Pause" disabled={!playing} onClick={() => control('pause')}>
          <Pause size={15} aria-hidden />
        </button>
        {DEBUG && (
          <button type="button" className="btn-icon" aria-label="Step one hour" disabled={finished} onClick={() => control('step')}>
            <StepForward size={15} aria-hidden />
          </button>
        )}
        {confirmReset ? (
          <span className="ml-1 flex flex-wrap items-center gap-1.5 text-xs font-semibold" role="alertdialog" aria-label="Confirm reset">
            Restart the week?
            <button
              type="button"
              className="btn"
              autoFocus
              onClick={() => {
                setConfirmReset(false)
                void control('reset')
              }}
            >
              Restart
            </button>
            <button
              type="button"
              className="btn"
              title="Rain on Day 2 10:00, cold-chain delay on Day 3, a Frame 3 scan on Day 4 14:00"
              onClick={() => {
                setConfirmReset(false)
                void control('reset', { scenario: 'demo' })
              }}
            >
              Demo script
            </button>
            <button type="button" className="btn" onClick={() => setConfirmReset(false)}>
              Keep run
            </button>
          </span>
        ) : (
          <button type="button" className="btn-icon" aria-label="Restart the week" onClick={() => setConfirmReset(true)}>
            <RotateCcw size={15} aria-hidden />
          </button>
        )}
      </div>

      <div className="min-w-[230px] flex-1 sm:max-w-xs">
        <div className="flex items-baseline justify-between gap-2 whitespace-nowrap text-xs font-semibold">
          <span>
            Simulated week · <span className="text-accent">{simClock(snap.tick)}</span>
          </span>
          <span className="text-muted">
            hour {snap.tick}/{CYCLE_TICKS}
          </span>
        </div>
        <div
          className="mt-1 h-1.5 overflow-hidden rounded-full bg-line"
          role="progressbar"
          aria-label="Week progress"
          aria-valuemin={0}
          aria-valuemax={CYCLE_TICKS}
          aria-valuenow={snap.tick}
        >
          <div className="h-full rounded-full bg-accent" style={{ width: `${(snap.tick / CYCLE_TICKS) * 100}%` }} />
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2 sm:ml-auto" role="group" aria-label="Disruptions">
        <span className="hidden text-xs font-semibold text-muted sm:inline">Test a disruption:</span>
        <button type="button" className="btn" disabled={finished || !!storm} onClick={() => triggerEvent('rainstorm')}>
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
    </section>
  )
}
