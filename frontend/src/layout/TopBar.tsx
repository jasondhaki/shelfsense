import { ChevronDown, MapPin } from 'lucide-react'
import { greeting } from '../lib/insights'
import { simClock } from '../lib/format'
import { useSim } from '../store/simStore'
import AlertsBell from './AlertsBell'
import ProfileMenu from './ProfileMenu'

function Subtitle() {
  const k = useSim((s) => s.snapshot?.kpis)
  const status = useSim((s) => s.snapshot?.status)
  if (!k) return <>Connecting to the store simulation…</>
  if (k.waste_reduction_pct === null)
    return <>Press play to run the week — your store and a baseline store get the same shoppers.</>
  const done = status === 'finished'
  return k.waste_reduction_pct >= 0 ? (
    <>
      Your store’s food waste is down by <strong className="text-accent">{k.waste_reduction_pct.toFixed(1)}%</strong>{' '}
      {done ? 'this simulated week' : 'so far this simulated week'}.
    </>
  ) : (
    <>Your store is wasting {Math.abs(k.waste_reduction_pct).toFixed(1)}% more than the baseline so far.</>
  )
}

export default function TopBar() {
  const name = useSim((s) => s.profile.name)
  const store = useSim((s) => s.profile.store)
  const which = useSim((s) => s.eslStore)
  const setWhich = useSim((s) => s.setEslStore)
  const connection = useSim((s) => s.connection)
  const snap = useSim((s) => s.snapshot)

  const live = connection === 'open'
  const statusText = !live
    ? connection === 'closed'
      ? 'Reconnecting…'
      : 'Connecting…'
    : snap?.status === 'playing'
      ? `System live · ${simClock(snap.tick)}`
      : snap?.status === 'finished'
        ? 'Week complete'
        : `Paused · ${simClock(snap?.tick ?? 0)}`

  return (
    <header className="flex flex-wrap items-center gap-x-4 gap-y-3">
      <div className="mr-auto min-w-0">
        <h1 className="text-2xl font-extrabold tracking-tight sm:text-[28px]">
          {greeting()}, {name} <span aria-hidden>👋</span>
        </h1>
        <p className="text-[15px] text-text/80">
          <Subtitle />
        </p>
      </div>

      <label className="relative flex items-center gap-2 rounded-full border border-line bg-panel py-2 pl-3.5 pr-9 text-sm font-semibold shadow-sm">
        <MapPin size={18} aria-hidden className="text-muted" />
        <span className="sr-only">Which store’s shelves to show</span>
        <select
          value={which}
          onChange={(e) => setWhich(e.target.value as 'A' | 'B')}
          className="appearance-none bg-transparent pr-1 font-semibold focus:outline-none"
        >
          <option value="B">Store: {store}</option>
          <option value="A">{store} — baseline twin</option>
        </select>
        <ChevronDown size={16} aria-hidden className="pointer-events-none absolute right-3 text-muted" />
      </label>

      <span
        className="flex items-center gap-2 rounded-full border border-line bg-panel px-3.5 py-2 text-sm font-semibold shadow-sm"
        role="status"
      >
        <span
          className={`h-2.5 w-2.5 rounded-full ${live ? (snap?.status === 'playing' ? 'bg-ok motion-safe:animate-pulse' : 'bg-ok') : 'bg-warn'}`}
          aria-hidden
        />
        {statusText}
      </span>

      <span className="hidden h-8 w-px bg-line sm:block" aria-hidden />
      <AlertsBell />
      <ProfileMenu />
    </header>
  )
}
