import { useState } from 'react'
import PageHead from '../components/PageHead'
import { useT } from '../lib/i18n'
import { useSim } from '../store/simStore'

export default function Settings() {
  const profile = useSim((s) => s.profile)
  const saveProfile = useSim((s) => s.saveProfile)
  const auth = useSim((s) => s.auth)
  const user = useSim((s) => s.user)
  const signOut = useSim((s) => s.signOut)
  const [saving, setSaving] = useState(false)
  const control = useSim((s) => s.control)
  const [name, setName] = useState(profile.name)
  const [store, setStore] = useState(profile.store)
  const [saved, setSaved] = useState(false)
  const t = useT()

  const dirty = name.trim() !== profile.name || store.trim() !== profile.store
  const valid = name.trim().length > 0 && store.trim().length > 0

  return (
    <>
      <PageHead
        title={t('Settings')}
        lead={
          auth === 'signed_in'
            ? t('Your profile is saved to your account and follows you to any device.')
            : t('You’re a guest: this profile is kept in this browser only.')
        }
      />
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <form
          className="zone space-y-4 p-4"
          onSubmit={async (e) => {
            e.preventDefault()
            if (!valid) return
            setSaving(true)
            setSaved(await saveProfile({ name: name.trim(), store: store.trim() }))
            setSaving(false)
          }}
        >
          <h3 className="h-card">{t('Profile')}</h3>
          {user && (
            <p className="text-sm">
              {t('Signed in as')} <strong>{user.email}</strong>
            </p>
          )}
          <label className="block">
            <span className="text-sm font-semibold">{t('Your name')}</span>
            <input
              value={name}
              maxLength={40}
              onChange={(e) => {
                setName(e.target.value)
                setSaved(false)
              }}
              className="mt-1 w-full rounded-xl border border-line bg-panel px-3 py-2 text-sm focus:border-accent focus:outline-none"
              autoComplete="given-name"
            />
          </label>
          <label className="block">
            <span className="text-sm font-semibold">{t('Store name')}</span>
            <input
              value={store}
              maxLength={40}
              onChange={(e) => {
                setStore(e.target.value)
                setSaved(false)
              }}
              className="mt-1 w-full rounded-xl border border-line bg-panel px-3 py-2 text-sm focus:border-accent focus:outline-none"
            />
          </label>
          {!valid && <p className="text-xs text-crit">{t('Name and store can’t be empty.')}</p>}
          <div className="flex items-center gap-3">
            <button type="submit" className="btn-primary" disabled={!dirty || !valid || saving}>
              {t(saving ? 'Saving…' : 'Save profile')}
            </button>
            {saved && (
              <span role="status" className="text-xs font-semibold text-accent">
                {t('Profile saved')}
              </span>
            )}
          </div>
        </form>

        <section aria-labelledby="sim-title" className="zone space-y-3 p-4">
          <h3 id="sim-title" className="h-card">
            {t('Simulation')}
          </h3>
          <p className="text-sm text-muted">
            {t('Each browser tab runs its own week. Restarting replays the same shoppers (same random seed), so results are reproducible.')}
          </p>
          <div className="flex flex-wrap gap-2">
            <button type="button" className="btn" onClick={() => control('reset')}>
              {t('Restart the week')}
            </button>
            <button type="button" className="btn" onClick={() => control('reset', { scenario: 'demo' })}>
              {t('Restart with the demo script')}
            </button>
          </div>
          <p className="text-xs text-muted">
            {auth === 'signed_in'
              ? t('Your week runs on the server under your account, so you can pick it up in another tab or device. A server restart starts a new week.')
              : t('Create an account to keep your store name and pick your week up on another device.')}
          </p>
          <button type="button" className="btn" onClick={signOut}>
            {t(auth === 'signed_in' ? 'Sign out' : 'Sign in or create an account')}
          </button>
          <p className="text-xs text-muted">
            {t('Demo script: rain on Day 2 at 10:00, a cold-chain delay on Day 3, and a damaged-strawberry scan on Day 4 at 14:00.')}
          </p>
        </section>
      </div>
    </>
  )
}
