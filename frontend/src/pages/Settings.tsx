import { useState } from 'react'
import PageHead from '../components/PageHead'
import { useSim } from '../store/simStore'

export default function Settings() {
  const profile = useSim((s) => s.profile)
  const setProfile = useSim((s) => s.setProfile)
  const control = useSim((s) => s.control)
  const [name, setName] = useState(profile.name)
  const [store, setStore] = useState(profile.store)
  const [saved, setSaved] = useState(false)

  const dirty = name.trim() !== profile.name || store.trim() !== profile.store
  const valid = name.trim().length > 0 && store.trim().length > 0

  return (
    <>
      <PageHead title="Settings" lead="Your profile is saved in this browser only." />
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <form
          className="zone space-y-4 p-4"
          onSubmit={(e) => {
            e.preventDefault()
            if (!valid) return
            setProfile({ name: name.trim(), store: store.trim() })
            setSaved(true)
          }}
        >
          <h3 className="h-card">Profile</h3>
          <label className="block">
            <span className="text-sm font-semibold">Your name</span>
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
            <span className="text-sm font-semibold">Store name</span>
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
          {!valid && <p className="text-xs text-crit">Name and store can’t be empty.</p>}
          <div className="flex items-center gap-3">
            <button type="submit" className="btn-primary" disabled={!dirty || !valid}>
              Save profile
            </button>
            {saved && (
              <span role="status" className="text-xs font-semibold text-accent">
                Profile saved
              </span>
            )}
          </div>
        </form>

        <section aria-labelledby="sim-title" className="zone space-y-3 p-4">
          <h3 id="sim-title" className="h-card">
            Simulation
          </h3>
          <p className="text-sm text-muted">
            Each browser tab runs its own week. Restarting replays the same shoppers (same random seed), so
            results are reproducible.
          </p>
          <div className="flex flex-wrap gap-2">
            <button type="button" className="btn" onClick={() => control('reset')}>
              Restart the week
            </button>
            <button type="button" className="btn" onClick={() => control('reset', { scenario: 'demo' })}>
              Restart with the demo script
            </button>
          </div>
          <p className="text-xs text-muted">
            Demo script: rain on Day 2 at 10:00, a cold-chain delay on Day 3, and a damaged-strawberry scan on Day 4
            at 14:00.
          </p>
        </section>
      </div>
    </>
  )
}
