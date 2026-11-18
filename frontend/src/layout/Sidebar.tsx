import { Leaf } from 'lucide-react'
import { useT } from '../lib/i18n'
import { useSim } from '../store/simStore'
import { FOOT, NAV } from './nav'

function Item({ id, label, Icon }: (typeof NAV)[number]) {
  const page = useSim((s) => s.page)
  const setPage = useSim((s) => s.setPage)
  const on = page === id
  const t = useT()
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
        {t(label)}
      </a>
    </li>
  )
}

export default function Sidebar() {
  const t = useT()

  return (
    <aside className="sticky top-0 hidden h-screen w-[260px] shrink-0 flex-col bg-gradient-to-b from-forest-900 to-forest-950 px-4 py-6 text-white lg:flex">
      <div className="flex items-center gap-3 px-2">
        <span className="grid h-11 w-11 place-items-center rounded-2xl bg-gradient-to-br from-[#4ADE80] to-[#15803D] shadow-lg">
          <Leaf size={24} aria-hidden className="text-white" />
        </span>
        <div>
          <div className="text-xl font-extrabold leading-tight tracking-tight">ShelfSense</div>
          <div className="text-xs text-white/70">{t('Food Waste Zero')}</div>
        </div>
      </div>

      <nav aria-label={t('Main')} className="mt-8 flex min-h-0 flex-1 flex-col overflow-y-auto">
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
      </nav>
    </aside>
  )
}
