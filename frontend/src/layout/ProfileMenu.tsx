import { CircleHelp, LogIn, LogOut, Settings, User } from 'lucide-react'
import { useCallback, useRef, useState } from 'react'
import { useDismiss } from '../lib/useDismiss'
import { useT } from '../lib/i18n'
import { useSim } from '../store/simStore'

export default function ProfileMenu() {
  const profile = useSim((s) => s.profile)
  const setPage = useSim((s) => s.setPage)
  const user = useSim((s) => s.user)
  const signOut = useSim((s) => s.signOut)
  const t = useT()
  const [open, setOpen] = useState(false)
  const root = useRef<HTMLDivElement>(null)
  const close = useCallback(() => setOpen(false), [])
  useDismiss(root, open, close)

  const go = (p: 'settings' | 'help') => {
    close()
    setPage(p)
  }

  return (
    <div ref={root} className="relative">
      <button
        type="button"
        aria-label={t('Profile: {name}', { name: profile.name })}
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        className="grid h-10 w-10 place-items-center rounded-full bg-forest-800 sm:h-12 sm:w-12 text-white ring-2 ring-panel hover:bg-forest-700"
      >
        <User size={26} aria-hidden fill="currentColor" strokeWidth={1.5} />
      </button>
      {open && (
        <div className="absolute right-0 z-30 mt-2 w-60 rounded-2xl border border-line bg-panel p-2 shadow-card">
          <div className="px-3 py-2">
            <div className="text-sm font-bold">{profile.name}</div>
            <div className="truncate text-xs text-muted">{user ? user.email : t('Guest — nothing is saved')}</div>
            <div className="text-xs text-muted">{t('Store: {name}', { name: profile.store })}</div>
          </div>
          <hr className="my-1 border-line" />
          <button type="button" className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold hover:bg-panel-2" onClick={() => go('settings')}>
            <Settings size={16} aria-hidden /> {t('Profile & settings')}
          </button>
          <button type="button" className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold hover:bg-panel-2" onClick={() => go('help')}>
            <CircleHelp size={16} aria-hidden /> {t('Help')}
          </button>
          <hr className="my-1 border-line" />
          <button type="button" className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold hover:bg-panel-2" onClick={signOut}>
            {user ? <LogOut size={16} aria-hidden /> : <LogIn size={16} aria-hidden />}
            {user ? t('Sign out') : t('Sign in or create account')}
          </button>
        </div>
      )}
    </div>
  )
}
