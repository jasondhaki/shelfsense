import { Leaf } from 'lucide-react'
import { useT } from '../lib/i18n'
import { useSim } from '../store/simStore'
import { FOOT, NAV } from './nav'

/** Below lg the sidebar becomes a scrollable tab strip. */
export default function MobileNav() {
  const page = useSim((s) => s.page)
  const setPage = useSim((s) => s.setPage)
  const t = useT()
  return (
    <nav aria-label={t('Main')} className="sticky top-0 z-20 bg-forest-900 px-4 pb-2 pt-3 shadow-md lg:hidden">
      <div className="mb-2 flex items-center gap-2 text-white">
        <span className="grid h-7 w-7 place-items-center rounded-lg bg-gradient-to-br from-[#4ADE80] to-[#15803D]">
          <Leaf size={16} aria-hidden />
        </span>
        <span className="font-extrabold tracking-tight">ShelfSense</span>
        <span className="text-xs text-white/60">{t('Food Waste Zero')}</span>
      </div>
      <ul className="no-scrollbar -mx-4 flex gap-1 overflow-x-auto px-4">
        {[...NAV, ...FOOT].map(({ id, label, Icon }) => (
          <li key={id}>
            <button
              type="button"
              aria-current={page === id ? 'page' : undefined}
              onClick={(e) => {
                setPage(id)
                e.currentTarget.scrollIntoView({ inline: 'center', block: 'nearest' })
              }}
              className={`flex items-center gap-1.5 whitespace-nowrap rounded-full px-3 py-1.5 text-xs font-semibold ${page === id ? 'bg-forest-700 text-white' : 'text-white/75'}`}
            >
              <Icon size={14} aria-hidden />
              {t(label)}
            </button>
          </li>
        ))}
      </ul>
    </nav>
  )
}
