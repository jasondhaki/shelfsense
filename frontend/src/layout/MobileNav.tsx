import { Leaf, LayoutGrid, Menu, X } from 'lucide-react'
import { useRef } from 'react'
import LangToggle from '../components/LangToggle'
import ThemeToggle from '../components/ThemeToggle'
import { useT } from '../lib/i18n'
import { useSim, type Page } from '../store/simStore'
import AlertsBell from './AlertsBell'
import { FOOT, NAV } from './nav'
import ProfileMenu from './ProfileMenu'

const TABS: Page[] = ['dashboard', 'inventory', 'forecast']

function Brand() {
  const t = useT()
  return (
    <div className="flex min-w-0 items-center gap-2">
      <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-gradient-to-br from-[#4ADE80] to-[#15803D] text-white">
        <Leaf size={20} aria-hidden />
      </span>
      <div className="min-w-0 leading-tight">
        <div className="text-lg font-extrabold tracking-tight">ShelfSense</div>
        <div className="truncate text-xs text-muted">{t('Food Waste Zero')}</div>
      </div>
    </div>
  )
}

/** Below lg: an app bar with a hamburger drawer (every page + language/theme), and a bottom tab
 *  bar for the three most used pages. The drawer is a native modal <dialog>: focus trap,
 *  Escape and the backdrop come with it. */
export default function MobileNav() {
  const page = useSim((s) => s.page)
  const setPage = useSim((s) => s.setPage)
  const drawer = useRef<HTMLDialogElement>(null)
  const t = useT()

  const go = (id: Page) => {
    setPage(id)
    drawer.current?.close()
    window.scrollTo({ top: 0 })
  }
  const open = () => drawer.current?.showModal()

  return (
    <>
      <header className="sticky top-0 z-20 flex items-center gap-2 border-b border-line/60 bg-bg/90 px-3 py-2 backdrop-blur-md lg:hidden">
        <button type="button" className="grid h-11 w-11 shrink-0 place-items-center rounded-full hover:bg-panel" aria-label={t('Open menu')} onClick={open}>
          <Menu size={26} aria-hidden strokeWidth={2} />
        </button>
        <Brand />
        <div className="ml-auto flex items-center gap-1">
          <AlertsBell />
          <ProfileMenu />
        </div>
      </header>

      <dialog
        ref={drawer}
        aria-label={t('Main')}
        onClick={(e) => e.target === e.currentTarget && drawer.current?.close()}
        className="m-0 h-full max-h-none w-[min(84vw,320px)] max-w-none bg-transparent p-0 backdrop:bg-black/50 backdrop:backdrop-blur-sm lg:hidden"
      >
        <nav className="flex h-full flex-col bg-gradient-to-b from-forest-900 to-forest-950 px-4 py-4 text-white">
          <div className="flex items-center justify-between gap-2 text-white [&_.text-muted]:text-white/70">
            <Brand />
            <button type="button" className="grid h-11 w-11 place-items-center rounded-full hover:bg-white/10" aria-label={t('Close menu')} onClick={() => drawer.current?.close()}>
              <X size={22} aria-hidden />
            </button>
          </div>
          <ul className="mt-6 flex-1 space-y-1 overflow-y-auto">
            {[...NAV, ...FOOT].map(({ id, label, Icon }) => (
              <li key={id}>
                <button
                  type="button"
                  aria-current={page === id ? 'page' : undefined}
                  onClick={() => go(id)}
                  className={`flex w-full items-center gap-3 rounded-xl px-3.5 py-3 text-[15px] font-semibold ${
                    page === id ? 'bg-forest-700 text-white' : 'text-white/80 hover:bg-white/5'
                  }`}
                >
                  <Icon size={20} aria-hidden strokeWidth={1.8} />
                  {t(label)}
                </button>
              </li>
            ))}
          </ul>
          <div className="mt-4 flex items-center gap-2 border-t border-white/10 pt-4 [&_button]:text-white [&_button:hover]:bg-white/10">
            <LangToggle />
            <ThemeToggle />
          </div>
        </nav>
      </dialog>

      <nav aria-label={t('Main')} className="fixed inset-x-3 bottom-3 z-20 rounded-3xl border border-line bg-panel/95 p-1.5 shadow-card backdrop-blur-md lg:hidden" style={{ marginBottom: 'env(safe-area-inset-bottom)' }}>
        <ul className="grid grid-cols-4 gap-1">
          {NAV.filter((n) => TABS.includes(n.id)).map(({ id, label, Icon }) => (
            <li key={id}>
              <button
                type="button"
                aria-current={page === id ? 'page' : undefined}
                onClick={() => go(id)}
                className={`flex w-full flex-col items-center gap-0.5 rounded-2xl py-2 text-xs font-semibold ${
                  page === id ? 'bg-forest-800 text-white dark:bg-accent dark:text-forest-950' : 'text-text/80 hover:bg-panel-2'
                }`}
              >
                <Icon size={22} aria-hidden strokeWidth={1.8} />
                {t(label)}
              </button>
            </li>
          ))}
          <li>
            <button
              type="button"
              onClick={open}
              aria-haspopup="dialog"
              className={`flex w-full flex-col items-center gap-0.5 rounded-2xl py-2 text-xs font-semibold ${
                TABS.includes(page) ? 'text-text/80 hover:bg-panel-2' : 'bg-forest-800 text-white dark:bg-accent dark:text-forest-950'
              }`}
            >
              <LayoutGrid size={22} aria-hidden strokeWidth={1.8} />
              {t('More')}
            </button>
          </li>
        </ul>
      </nav>
    </>
  )
}
