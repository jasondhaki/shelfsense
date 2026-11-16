import { useSim } from '../store/simStore'
import { FOOT, NAV } from './nav'

/** Below lg the sidebar becomes a scrollable tab strip. */
export default function MobileNav() {
  const page = useSim((s) => s.page)
  const setPage = useSim((s) => s.setPage)
  return (
    <nav aria-label="Main" className="overflow-x-auto bg-forest-900 px-4 py-2 lg:hidden">
      <ul className="flex gap-1">
        {[...NAV, ...FOOT].map(({ id, label, Icon }) => (
          <li key={id}>
            <button
              type="button"
              aria-current={page === id ? 'page' : undefined}
              onClick={() => setPage(id)}
              className={`flex items-center gap-1.5 whitespace-nowrap rounded-full px-3 py-1.5 text-xs font-semibold ${page === id ? 'bg-forest-700 text-white' : 'text-white/75'}`}
            >
              <Icon size={14} aria-hidden />
              {label}
            </button>
          </li>
        ))}
      </ul>
    </nav>
  )
}
