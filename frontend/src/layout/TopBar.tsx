import { ChevronDown, MapPin } from 'lucide-react'
import { greeting } from '../lib/insights'
import { simClock } from '../lib/format'
import { rich, useT } from '../lib/i18n'
import { useSim } from '../store/simStore'
import LangToggle from '../components/LangToggle'
import ThemeToggle from '../components/ThemeToggle'
import AlertsBell from './AlertsBell'
import ProfileMenu from './ProfileMenu'

function Subtitle() {
  const k = useSim((s) => s.snapshot?.kpis)
  const status = useSim((s) => s.snapshot?.status)
  const t = useT()
  if (!k) return <>{t('Connecting to the store simulation…')}</>
  if (k.waste_reduction_pct === null)
    return <>{t('Press play to run the week — your store and a baseline store get the same shoppers.')}</>
  const done = status === 'finished'
  return k.waste_reduction_pct >= 0 ? (
    <>
      {rich(
        t(done ? 'Your store’s food waste is down by {pct} this simulated week.' : 'Your store’s food waste is down by {pct} so far this simulated week.'),
        { pct: <strong className="text-accent">{k.waste_reduction_pct.toFixed(1)}%</strong> },
      )}
    </>
  ) : (
    <>{t('Your store is wasting {pct}% more than the baseline so far.', { pct: Math.abs(k.waste_reduction_pct).toFixed(1) })}</>
  )
}

export default function TopBar() {
  const name = useSim((s) => s.profile.name)
  const store = useSim((s) => s.profile.store)
  const which = useSim((s) => s.eslStore)
  const setWhich = useSim((s) => s.setEslStore)
  const connection = useSim((s) => s.connection)
  const snap = useSim((s) => s.snapshot)
  const t = useT()

  const live = connection === 'open'
  const statusText = !live
    ? connection === 'closed'
      ? t('Reconnecting…')
      : t('Connecting…')
    : snap?.status === 'playing'
      ? `${t('System live')} · ${simClock(snap.tick)}`
      : snap?.status === 'finished'
        ? t('Week complete')
        : `${t('Paused')} · ${simClock(snap?.tick ?? 0)}`

  return (
    <header className="flex flex-wrap items-center gap-x-4 gap-y-3">
      {/* phones: greeting + bell/avatar on row 1, store/status on row 2; desktop: one row */}
      <div className="order-1 min-w-0 flex-1">
        <h1 className="text-xl font-extrabold tracking-tight sm:text-[28px]">
          {greeting(t)}, {name} <span aria-hidden>👋</span>
        </h1>
        <p className="text-sm text-text/80 sm:text-[15px]">
          <Subtitle />
        </p>
      </div>

      <div className="order-3 flex basis-full flex-wrap items-center gap-2 sm:gap-3 lg:order-2 lg:basis-auto">
        <label className="relative flex items-center gap-1.5 rounded-full border border-line bg-panel py-1.5 pl-3 pr-8 text-xs font-semibold shadow-sm sm:gap-2 sm:py-2 sm:pl-3.5 sm:pr-9 sm:text-sm">
          <MapPin size={16} aria-hidden className="text-muted" />
          <span className="sr-only">{t('Which store’s shelves to show')}</span>
          <select
            value={which}
            onChange={(e) => setWhich(e.target.value as 'A' | 'B')}
            className="appearance-none bg-transparent pr-1 font-semibold focus:outline-none"
          >
            <option value="B">{t('Store: {name}', { name: store })}</option>
            <option value="A">{t('Baseline twin')}</option>
          </select>
          <ChevronDown size={16} aria-hidden className="pointer-events-none absolute right-3 text-muted" />
        </label>

        <span
          className="flex items-center gap-2 rounded-full border border-line bg-panel px-3 py-1.5 text-xs font-semibold shadow-sm sm:px-3.5 sm:py-2 sm:text-sm"
          role="status"
        >
          <span
            className={`h-2.5 w-2.5 rounded-full ${live ? (snap?.status === 'playing' ? 'bg-ok motion-safe:animate-pulse' : 'bg-ok') : 'bg-warn'}`}
            aria-hidden
          />
          {statusText}
        </span>
      </div>

      <div className="order-2 flex items-center gap-1 sm:gap-3 lg:order-3">
        <span className="hidden h-8 w-px bg-line lg:block" aria-hidden />
        <LangToggle />
        <ThemeToggle />
        <AlertsBell />
        <ProfileMenu />
      </div>
    </header>
  )
}
