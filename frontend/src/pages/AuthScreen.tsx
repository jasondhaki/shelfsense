import { ArrowLeft, ArrowRight, Leaf, LoaderCircle, MailCheck } from 'lucide-react'
import { useEffect, useState, type FormEvent } from 'react'
import { api } from '../lib/api'
import { useSim } from '../store/simStore'

type Mode = 'signin' | 'signup'

const FACTS: [string, string][] = [
  ['57.8%', 'less food wasted than a printed-date store (20 simulated weeks)'],
  ['8', 'fresh lines priced every hour from real shelf-life data'],
  ['5', 'AI agents that explain every price and order they set'],
]

function Field({
  label,
  hint,
  ...input
}: { label: string; hint?: string } & React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <label className="block">
      <span className="text-sm font-semibold">{label}</span>
      <input
        {...input}
        className="mt-1 w-full rounded-xl border border-line bg-panel px-3.5 py-2.5 text-sm focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20"
      />
      {hint && <span className="mt-1 block text-xs text-muted">{hint}</span>}
    </label>
  )
}

export default function AuthScreen() {
  const signIn = useSim((s) => s.signIn)
  const signUp = useSim((s) => s.signUp)
  const verifyEmail = useSim((s) => s.verifyEmail)
  const continueAsGuest = useSim((s) => s.continueAsGuest)
  const [mode, setMode] = useState<Mode>('signin')
  const [busy, setBusy] = useState(false)
  const [slow, setSlow] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [accounts, setAccounts] = useState(true)
  const [emailSignup, setEmailSignup] = useState(true)
  const [f, setF] = useState({ email: '', password: '', name: '', store: '' })
  const [pending, setPending] = useState<string | null>(null) // "enter the code we emailed…"
  const [code, setCode] = useState('')

  useEffect(() => {
    api
      .health()
      .then((h) => {
        setAccounts(h.accounts !== 'off')
        setEmailSignup(h.email_signup !== false)
      })
      .catch(() => undefined) // a sleeping server answers later; the form still works
  }, [])

  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement>) => setF({ ...f, [k]: e.target.value })

  const run = async <T,>(work: () => Promise<T>): Promise<T> => {
    setBusy(true)
    setError(null)
    const t = window.setTimeout(() => setSlow(true), 3000)
    try {
      return await work()
    } finally {
      window.clearTimeout(t)
      setSlow(false)
      setBusy(false)
    }
  }

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    const r = await run(() =>
      mode === 'signin'
        ? signIn(f.email, f.password)
        : signUp({ email: f.email, password: f.password, name: f.name, store: f.store }),
    )
    setError(r.error)
    if (r.verify) {
      setCode('')
      setPending(r.verify)
    }
  }

  const submitCode = async (e: FormEvent) => {
    e.preventDefault()
    setError(await run(() => verifyEmail(f.email, f.password, code)))
  }

  // signing in with an unverified address emails a fresh code (at most one a minute)
  const resend = async () => {
    const r = await run(() => signIn(f.email, f.password))
    setError(r.error)
    if (r.verify) setPending(r.verify)
  }

  return (
    <div className="grid min-h-full lg:grid-cols-[minmax(0,1.05fr)_minmax(0,1fr)]">
      <section className="relative overflow-hidden bg-gradient-to-br from-forest-800 via-forest-900 to-forest-950 px-6 py-8 text-white sm:px-10 lg:px-14 lg:py-14">
        <div
          className="pointer-events-none absolute -right-24 -top-24 h-80 w-80 rounded-full bg-[#4ADE80]/10 blur-3xl"
          aria-hidden
        />
        <div className="relative flex items-center gap-3">
          <span className="grid h-11 w-11 place-items-center rounded-2xl bg-gradient-to-br from-[#4ADE80] to-[#15803D] shadow-lg">
            <Leaf size={24} aria-hidden />
          </span>
          <div>
            <div className="text-xl font-extrabold leading-tight tracking-tight">ShelfSense</div>
            <div className="text-xs text-white/70">Food Waste Zero</div>
          </div>
        </div>
        <h1 className="relative mt-10 max-w-[18ch] text-3xl font-extrabold leading-[1.1] tracking-tight sm:text-4xl lg:mt-20 lg:text-5xl">
          Sell it before it spoils.
        </h1>
        <p className="relative mt-4 max-w-[46ch] text-[15px] leading-relaxed text-white/80">
          ShelfSense reprices fresh food by how much shelf life is really left, and orders only what will sell.
          Run a week of your store next to a printed-date twin and see the difference.
        </p>
        <dl className="relative mt-8 hidden gap-4 sm:grid sm:grid-cols-3 lg:mt-14 lg:grid-cols-1 lg:gap-5">
          {FACTS.map(([n, t]) => (
            <div key={t} className="flex items-baseline gap-3 border-t border-white/10 pt-3 lg:max-w-md">
              <dt className="text-2xl font-extrabold text-[#4ADE80] lg:text-3xl">{n}</dt>
              <dd className="text-sm text-white/75">{t}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section className="flex items-center justify-center px-4 py-8 sm:px-8">
        <div className="w-full max-w-md">
          {pending ? (
            <form onSubmit={submitCode} className="space-y-4">
              <span className="grid h-12 w-12 place-items-center rounded-2xl bg-accent/10 text-accent">
                <MailCheck size={24} aria-hidden />
              </span>
              <h2 className="text-2xl font-extrabold tracking-tight">Check your email</h2>
              <p role="status" className="text-sm text-muted">
                {pending} It expires in 15 minutes; check spam if it isn’t there.
              </p>
              <Field
                label="6-digit code"
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                required
                inputMode="numeric"
                autoComplete="one-time-code"
                pattern="[0-9]{6}"
                maxLength={6}
                autoFocus
              />
              {error && (
                <p role="alert" className="rounded-xl bg-crit/[0.07] px-3 py-2 text-sm text-crit">
                  {error}
                </p>
              )}
              <button type="submit" className="btn-primary w-full justify-center py-3 text-sm" disabled={busy || code.length !== 6}>
                {busy ? <LoaderCircle size={16} aria-hidden className="motion-safe:animate-spin" /> : null}
                {busy ? 'Checking…' : 'Verify and open my dashboard'}
              </button>
              {slow && (
                <p role="status" className="text-center text-xs text-muted">
                  The free server is waking up — the first request can take up to a minute.
                </p>
              )}
              <div className="flex items-center justify-between text-sm">
                <button
                  type="button"
                  className="inline-flex items-center gap-1 font-semibold text-muted hover:text-text"
                  onClick={() => {
                    setPending(null)
                    setError(null)
                  }}
                >
                  <ArrowLeft size={15} aria-hidden /> Back
                </button>
                <button type="button" className="link font-semibold" disabled={busy} onClick={() => void resend()}>
                  Send a new code
                </button>
              </div>
            </form>
          ) : (
            <>
            <div role="tablist" aria-label="Account" className="mb-6 flex rounded-full border border-line bg-panel p-1">
              {(
                [
                  ['signin', 'Sign in'],
                  ['signup', 'Create account'],
                ] as const
              ).map(([id, label]) => (
                <button
                  key={id}
                  type="button"
                  role="tab"
                  aria-selected={mode === id}
                  onClick={() => {
                    setMode(id)
                    setError(null)
                  }}
                  className={`flex-1 rounded-full px-4 py-2 text-sm font-semibold ${mode === id ? 'bg-forest-800 text-white' : 'text-muted hover:text-text'}`}
                >
                  {label}
                </button>
              ))}
            </div>

            <h2 className="text-2xl font-extrabold tracking-tight">
              {mode === 'signin' ? 'Welcome back' : 'Set up your store'}
            </h2>
            <p className="mt-1 text-sm text-muted">
              {mode === 'signin'
                ? 'Sign in to open your own dashboard and simulated week.'
                : 'Your name and store appear on your dashboard. You can change them later.'}
            </p>

            {accounts && !emailSignup && mode === 'signup' && (
              <p role="status" className="mt-4 rounded-xl bg-warn/10 px-3 py-2 text-sm text-warn">
                New accounts are paused right now (email is offline). You can sign in or try ShelfSense as a guest.
              </p>
            )}

            {!accounts && (
              <p role="status" className="mt-4 rounded-xl bg-warn/10 px-3 py-2 text-sm text-warn">
                Accounts are offline right now. You can still try ShelfSense as a guest.
              </p>
            )}

            <form className="mt-5 space-y-4" onSubmit={submit} noValidate={false}>
              {mode === 'signup' && (
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <Field label="Your name" value={f.name} onChange={set('name')} required maxLength={40} autoComplete="name" />
                  <Field
                    label="Store name"
                    value={f.store}
                    onChange={set('store')}
                    required
                    maxLength={40}
                    placeholder="e.g. Bay 2"
                    autoComplete="organization"
                  />
                </div>
              )}
              <Field label="Email" type="email" value={f.email} onChange={set('email')} required autoComplete="email" />
              <Field
                label="Password"
                type="password"
                value={f.password}
                onChange={set('password')}
                required
                minLength={mode === 'signup' ? 8 : 1}
                autoComplete={mode === 'signin' ? 'current-password' : 'new-password'}
                hint={mode === 'signup' ? 'At least 8 characters.' : undefined}
              />
              {error && (
                <p role="alert" className="rounded-xl bg-crit/[0.07] px-3 py-2 text-sm text-crit">
                  {error}
                </p>
              )}
              <button type="submit" className="btn-primary w-full justify-center py-3 text-sm" disabled={busy || !accounts || (mode === 'signup' && !emailSignup)}>
                {busy ? <LoaderCircle size={16} aria-hidden className="motion-safe:animate-spin" /> : null}
                {busy ? (mode === 'signin' ? 'Signing in…' : 'Creating account…') : mode === 'signin' ? 'Sign in' : 'Create account'}
              </button>
              {slow && (
                <p role="status" className="text-center text-xs text-muted">
                  The free server is waking up — the first request can take up to a minute.
                </p>
              )}
            </form>

            <div className="my-6 flex items-center gap-3 text-xs text-muted" aria-hidden>
              <span className="h-px flex-1 bg-line" /> or <span className="h-px flex-1 bg-line" />
            </div>
            <button type="button" className="btn w-full justify-center py-3 text-sm" onClick={continueAsGuest}>
              Continue as guest <ArrowRight size={15} aria-hidden />
            </button>
            <p className="mt-2 text-center text-xs text-muted">
              Guests get a fresh week in this tab; nothing is saved. Accounts keep your week between visits.
            </p>
            </>
          )}
        </div>
      </section>
    </div>
  )
}
