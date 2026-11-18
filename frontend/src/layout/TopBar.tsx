import { MapPin } from 'lucide-react'
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
        <h1 className="text-2xl font-extrabold tracking-tight sm:text-[28px]">
          {greeting(t)}, {name} <span aria-hidden>👋</span>
        </h1>
        <p className="text-sm text-text/80 sm:text-[15px]">
          <Subtitle />
        </p>
      </div>

      <div className="order-3 grid basis-full grid-cols-2 items-center gap-2 sm:flex sm:flex-wrap sm:gap-3 lg:order-2 lg:basis-auto">
        <div
          role="radiogroup"
          aria-label={t('Which store’s shelves to show')}
          className="col-span-2 flex min-w-0 items-center gap-1 rounded-full border border-line bg-panel p-1 text-sm font-semibold shadow-sm sm:col-span-1"
        >
          {(['B', 'A'] as const).map((id) => (
            <button
              key={id}
              type="button"
              role="radio"
              aria-checked={which === id}
              title={id === 'B' ? t('ShelfSense store') : t('Baseline twin')}
              onClick={() => setWhich(id)}
              className={`flex min-w-0 flex-1 items-center justify-center gap-1.5 rounded-full px-3 py-1.5 transition-colors sm:flex-none ${
                which === id ? 'bg-forest-800 text-white shadow-sm' : 'text-muted hover:text-text'
              }`}
            >
              {id === 'B' && <MapPin size={15} aria-hidden className="shrink-0" />}
              <span className="truncate">{id === 'B' ? store : t('Baseline twin')}</span>
            </button>
          ))}
        </div>

        <span
          className="col-span-2 flex min-w-0 items-center gap-2 truncate rounded-full sm:col-span-1 border border-line bg-panel px-3 py-2.5 text-sm font-semibold shadow-sm sm:px-3.5 sm:py-2"
          role="status"
        >
          <span
            className={`h-2.5 w-2.5 rounded-full ${live ? (snap?.status === 'playing' ? 'bg-ok motion-safe:animate-pulse' : 'bg-ok') : 'bg-warn'}`}
            aria-hidden
          />
          {statusText}
        </span>
      </div>

      <div className="order-2 hidden items-center gap-3 lg:order-3 lg:flex">
        <span className="hidden h-8 w-px bg-line lg:block" aria-hidden />
        <LangToggle />
        <ThemeToggle />
        <AlertsBell />
        <ProfileMenu />
      </div>
    </header>
  )
}
