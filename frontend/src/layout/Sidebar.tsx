import { Leaf } from 'lucide-react'
import { CYCLE_TICKS } from '../lib/format'
import { useSim } from '../store/simStore'
import { FOOT, NAV } from './nav'

function Item({ id, label, Icon }: (typeof NAV)[number]) {
  const page = useSim((s) => s.page)
  const setPage = useSim((s) => s.setPage)
  const on = page === id
  return (
    <li>
      <a
        href={`#/${id}`}
        onClick={(e) => {
          e.preventDefault()
          setPage(id)
        }}
        aria-current={on ? 'page' : undefined}
        className={`flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-[15px] font-semibold transition-colors ${
          on
            ? 'border border-white/10 bg-forest-700 text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.08)]'
            : 'border border-transparent text-white/80 hover:bg-white/5 hover:text-white'
        }`}
      >
        <Icon size={20} aria-hidden strokeWidth={1.8} />
        {label}
      </a>
    </li>
  )
}

export default function Sidebar() {
  const kpis = useSim((s) => s.snapshot?.kpis)
  const tick = useSim((s) => s.snapshot?.tick ?? 0)
  const day = Math.min(Math.floor(tick / 24) + 1, 7)

  return (
    <aside className="sticky top-0 hidden h-screen w-[260px] shrink-0 flex-col bg-gradient-to-b from-forest-900 to-forest-950 px-4 py-6 text-white lg:flex">
      <div className="flex items-center gap-3 px-2">
        <span className="grid h-11 w-11 place-items-center rounded-2xl bg-gradient-to-br from-[#4ADE80] to-[#15803D] shadow-lg">
          <Leaf size={24} aria-hidden className="text-white" />
        </span>
        <div>
          <div className="text-xl font-extrabold leading-tight tracking-tight">ShelfSense</div>
          <div className="text-xs text-white/70">Food Waste Zero</div>
        </div>
      </div>

      <nav aria-label="Main" className="mt-8 flex min-h-0 flex-1 flex-col overflow-y-auto">
        <ul className="space-y-1">
          {NAV.map((n) => (
            <Item key={n.id} {...n} />
          ))}
        </ul>
        <hr className="mx-3 my-5 border-white/10" />
        <ul className="space-y-1">
          {FOOT.map((n) => (
            <Item key={n.id} {...n} />
          ))}
        </ul>

        <div className="mt-auto rounded-2xl border border-white/10 bg-gradient-to-b from-forest-800 to-forest-900 p-4">
          <div className="flex items-center gap-2 text-sm font-bold">
            <Leaf size={16} aria-hidden className="text-[#4ADE80]" />
            Reduce food waste
          </div>
          <p className="mt-1 text-xs leading-relaxed text-white/75">
            {kpis && kpis.food_diverted_kg > 0
              ? `${kpis.food_diverted_kg.toFixed(1)} kg kept out of the bin so far — day ${day} of 7.`
              : 'Run the simulated week to see how much food the AI store saves.'}
          </p>
          <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-white/10" aria-hidden>
            <div className="h-full rounded-full bg-[#4ADE80]" style={{ width: `${(tick / CYCLE_TICKS) * 100}%` }} />
          </div>
        </div>
      </nav>
    </aside>
  )
}
