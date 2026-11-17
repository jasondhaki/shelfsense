import {
  ArrowLeft,
  ArrowRight,
  Eye,
  EyeOff,
  KeyRound,
  LoaderCircle,
  LockKeyhole,
  Mail,
  Store,
  UserRound,
} from 'lucide-react'
import { useEffect, useId, useState, type FormEvent, type ReactNode } from 'react'
import type { LucideIcon } from 'lucide-react'
import { api } from '../lib/api'
import ThemeToggle from '../components/ThemeToggle'
import { useSim } from '../store/simStore'

/** Login from the owner's mock (login.jpg, light and dark rows): form left, produce photo behind a green wave
 *  right; on phones the photo becomes a corner blob. The mock's Google/Microsoft row is replaced
 *  by "Continue as guest" (no OAuth here), and "Forgot your password?" is a real email-code reset. */

type Mode = 'signin' | 'signup' | 'verify' | 'forgot' | 'reset'

const PHOTO = '/login-produce.jpg' // Unsplash, Michael Schmid (public/CREDITS.md)
const BRIGHT = '#2FB344' // headline accent + button: large text / fills only
const LINK = 'text-ok' // small green text: #15803D keeps 4.5:1 on white

function LeafMark({ size = 40 }: { size?: number }) {
  const id = useId()
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" aria-hidden>
      <defs>
        <linearGradient id={id} x1="0" y1="1" x2="1" y2="0">
          <stop offset="0" stopColor="#15803D" />
          <stop offset="1" stopColor="#6EE787" />
        </linearGradient>
      </defs>
      <path d="M6 42C6 20 20 7 44 5c0 24-13 38-34 38z" fill={`url(#${id})`} />
      <path d="M10 39C17 28 26 20 37 13" stroke="#fff" strokeWidth="2.6" strokeLinecap="round" fill="none" opacity=".85" />
    </svg>
  )
}

function Brand() {
  return (
    <div className="flex items-center justify-center gap-2.5 lg:justify-start">
      <LeafMark />
      <div className="text-left leading-tight">
        <div className="text-[22px] font-extrabold tracking-tight text-text">ShelfSense</div>
        <div className="text-[13px] font-medium text-muted">Food Waste Zero</div>
      </div>
    </div>
  )
}

function Title({ lead, accent }: { lead: string; accent: string }) {
  return (
    <h1 className="text-[34px] font-extrabold leading-tight tracking-tight text-text sm:text-[40px]">
      {lead} <span style={{ color: BRIGHT }}>{accent}</span>
    </h1>
  )
}

function Pill({
  icon: Icon,
  label,
  trailing,
  ...input
}: { icon: LucideIcon; label: string; trailing?: ReactNode } & React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <label className="relative block">
      <span className="sr-only">{label}</span>
      <Icon size={18} aria-hidden className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-text/70" />
      <input
        {...input}
        placeholder={label}
        className="h-12 w-full rounded-full border border-[#CFE3D5] bg-white pl-11 dark:border-white/20 dark:bg-white/[0.03] pr-12 text-[15px] text-text placeholder:text-muted/90 focus:border-[#3DBE4F] focus:outline-none focus:ring-4 focus:ring-[#3DBE4F]/15"
      />
      {trailing && <span className="absolute right-2 top-1/2 -translate-y-1/2">{trailing}</span>}
    </label>
  )
}

function PasswordPill(props: { label: string } & React.InputHTMLAttributes<HTMLInputElement>) {
  const [shown, setShown] = useState(false)
  return (
    <Pill
      {...props}
      icon={LockKeyhole}
      type={shown ? 'text' : 'password'}
      trailing={
        <button
          type="button"
          onClick={() => setShown(!shown)}
          aria-label={shown ? 'Hide password' : 'Show password'}
          aria-pressed={shown}
          className="grid h-9 w-9 place-items-center rounded-full text-text/70 hover:bg-mint hover:text-text"
        >
          {shown ? <EyeOff size={18} aria-hidden /> : <Eye size={18} aria-hidden />}
        </button>
      }
    />
  )
}

function Primary({ busy, children, disabled }: { busy: boolean; children: ReactNode; disabled?: boolean }) {
  return (
    <button
      type="submit"
      disabled={busy || disabled}
      className="flex h-12 w-full items-center justify-center gap-2 rounded-full bg-gradient-to-b from-[#62E077] to-[#2FB344] text-[16px] font-extrabold text-[#06240F] shadow-[0_8px_20px_-8px_rgba(47,179,68,0.7)] transition hover:brightness-105 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[#3DBE4F]/30 disabled:cursor-not-allowed disabled:opacity-60"
    >
      {busy && <LoaderCircle size={17} aria-hidden className="motion-safe:animate-spin" />}
      {children}
    </button>
  )
}

function Note({ tone, children }: { tone: 'error' | 'warn' | 'info'; children: ReactNode }) {
  const cls = {
    error: 'bg-crit/[0.07] text-crit',
    warn: 'bg-warn/10 text-warn',
    info: 'bg-mint text-ok',
  }[tone]
  return (
    <p role={tone === 'error' ? 'alert' : 'status'} className={`rounded-2xl px-4 py-2.5 text-left text-sm ${cls}`}>
      {children}
    </p>
  )
}

/** Same S-curve at three offsets: glow, green band, then the white form side. */
function wave(dx: number) {
  return `M0,0 H${120 + dx} C${60 + dx},180 ${30 + dx},270 ${85 + dx},430 C${140 + dx},590 ${125 + dx},780 ${35 + dx},1000 H0 Z`
}

function PhotoPanel() {
  const id = useId()
  return (
    <div className="relative hidden overflow-hidden lg:block" aria-hidden>
      <img src={PHOTO} alt="" className="absolute inset-0 h-full w-full object-cover" />
      <svg className="absolute inset-y-0 left-0 h-full w-[34%]" viewBox="0 0 200 1000" preserveAspectRatio="none">
        <defs>
          <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#7EE891" />
            <stop offset=".5" stopColor="#2FB344" />
            <stop offset="1" stopColor="#7EE891" />
          </linearGradient>
        </defs>
        <path d={wave(48)} fill="#C9F7D2" opacity=".85" className="dark:fill-[#14532D]" />
        <path d={wave(28)} fill={`url(#${id})`} />
        <path d={wave(0)} className="fill-white dark:fill-[#07130D]" />
      </svg>
    </div>
  )
}

/** Phones: the photo tucked into the top-right corner behind a green band. */
function PhotoBlob() {
  const id = useId().replace(/:/g, '')
  return (
    <div className="pointer-events-none absolute right-0 top-0 h-40 w-[64%] sm:h-44 lg:hidden" aria-hidden>
      <svg width="0" height="0" className="absolute">
        <clipPath id={`${id}-band`} clipPathUnits="objectBoundingBox">
          <path d="M0,0 C0.06,0.42 0.3,0.7 0.62,0.78 C0.84,0.84 0.96,0.92 1,1 L1,0 Z" />
        </clipPath>
        <clipPath id={`${id}-img`} clipPathUnits="objectBoundingBox">
          <path d="M0.12,0 C0.18,0.34 0.4,0.56 0.68,0.63 C0.86,0.68 0.96,0.76 1,0.86 L1,0 Z" />
        </clipPath>
      </svg>
      <div
        className="absolute inset-0 bg-gradient-to-br from-[#9BEFAA] via-[#3DBE4F] to-[#2FB344]"
        style={{ clipPath: `url(#${id}-band)` }}
      />
      <img src={PHOTO} alt="" className="absolute inset-0 h-full w-full object-cover" style={{ clipPath: `url(#${id}-img)` }} />
    </div>
  )
}

export default function AuthScreen() {
  const signIn = useSim((s) => s.signIn)
  const signUp = useSim((s) => s.signUp)
  const verifyEmail = useSim((s) => s.verifyEmail)
  const requestReset = useSim((s) => s.requestReset)
  const resetPassword = useSim((s) => s.resetPassword)
  const continueAsGuest = useSim((s) => s.continueAsGuest)

  const [mode, setMode] = useState<Mode>('signin')
  const [busy, setBusy] = useState(false)
  const [slow, setSlow] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [info, setInfo] = useState<string | null>(null) // "enter the code we emailed…"
  const [accounts, setAccounts] = useState(true)
  const [emailSignup, setEmailSignup] = useState(true)
  const [f, setF] = useState({ email: '', password: '', name: '', store: '', code: '' })

  useEffect(() => {
    api
      .health()
      .then((h) => {
        setAccounts(h.accounts !== 'off')
        setEmailSignup(h.email_signup !== false)
      })
      .catch(() => undefined) // a sleeping server answers later; the form still works
  }, [])

  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setF({ ...f, [k]: k === 'code' ? e.target.value.replace(/\D/g, '').slice(0, 6) : e.target.value })

  const go = (m: Mode) => {
    setMode(m)
    setError(null)
    setInfo(null)
    if (m === 'verify' || m === 'reset') setF((x) => ({ ...x, code: '' }))
  }

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
    if (mode === 'signin' || mode === 'signup') {
      const r = await run(() =>
        mode === 'signin'
          ? signIn(f.email, f.password)
          : signUp({ email: f.email, password: f.password, name: f.name, store: f.store }),
      )
      setError(r.error)
      if (r.verify) {
        go('verify')
        setInfo(r.verify)
      }
    } else if (mode === 'verify') {
      setError(await run(() => verifyEmail(f.email, f.password, f.code)))
    } else if (mode === 'forgot') {
      const r = await run(() => requestReset(f.email))
      setError(r.error)
      if (r.verify) {
        setF((x) => ({ ...x, password: '' }))
        go('reset')
        setInfo(r.verify)
      }
    } else {
      setError(await run(() => resetPassword(f.email, f.code, f.password)))
    }
  }

  // verify: signing in unverified re-sends; reset: asking again re-sends (both ≤ 1 a minute)
  const resend = async () => {
    const r = await run(() => (mode === 'verify' ? signIn(f.email, f.password) : requestReset(f.email)))
    setError(r.error)
    if (r.verify) setInfo(r.verify)
  }

  const head: Record<Mode, [string, string, string]> = {
    signin: ['Log', 'In', 'Access your ShelfSense dashboard'],
    signup: ['Sign', 'Up', 'Your own store, and a simulated week that’s saved for you'],
    verify: ['Check your', 'email', 'Enter the 6-digit code to finish creating your account'],
    forgot: ['Reset', 'password', 'We’ll email you a 6-digit code'],
    reset: ['New', 'password', 'Enter the code from your email and choose a new password'],
  }
  const [lead, accent, sub] = head[mode]
  const signupPaused = mode === 'signup' && accounts && !emailSignup
  const codeStep = mode === 'verify' || mode === 'reset'
  const label: Record<Mode, string> = busy
    ? { signin: 'Logging in…', signup: 'Creating account…', verify: 'Checking…', forgot: 'Sending…', reset: 'Saving…' }
    : {
        signin: 'Log In',
        signup: 'Create account',
        verify: 'Verify and open my dashboard',
        forgot: 'Email me a code',
        reset: 'Set password and log in',
      }

  return (
    <div className="relative min-h-full overflow-hidden bg-[#F3FAF5] dark:bg-[#04110A] sm:px-6 sm:py-8 lg:grid lg:place-items-center lg:px-10">
      {/* soft page swooshes, as in the mock's background */}
      <div className="pointer-events-none absolute -right-40 -top-40 hidden h-[520px] w-[520px] rounded-full bg-[#86EFAC]/35 blur-3xl dark:bg-[#22C55E]/20 sm:block" aria-hidden />
      <div className="pointer-events-none absolute -bottom-48 -left-40 hidden h-[520px] w-[520px] rounded-full bg-[#BBF7D0]/50 blur-3xl dark:bg-[#15803D]/25 sm:block" aria-hidden />

      <main className="relative mx-auto grid min-h-[100dvh] w-full overflow-hidden bg-white dark:bg-[#07130D] sm:min-h-0 sm:max-w-md sm:rounded-[32px] sm:border-2 sm:border-[#7EE891]/70 sm:shadow-[0_30px_80px_-30px_rgba(21,128,61,0.35)] dark:sm:border-[#4ADE80]/70 dark:sm:shadow-[0_0_60px_-20px_rgba(74,222,128,0.45)] lg:min-h-[640px] lg:max-w-[1120px] lg:grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)]">
        <PhotoBlob />
        {/* bottom swoosh on phones */}
        <svg className="pointer-events-none absolute -bottom-1 left-0 h-14 w-full lg:hidden" viewBox="0 0 400 60" preserveAspectRatio="none" aria-hidden>
          <path d="M0,60 V38 C90,18 170,58 260,40 C320,28 360,8 400,0 V60 Z" fill="#BBF7D0" className="dark:fill-[#14532D]" />
          <path d="M0,60 V48 C100,30 180,62 270,50 C330,42 370,24 400,16 V60 Z" fill="#3DBE4F" opacity=".55" />
        </svg>

        <section className="relative z-10 flex flex-col justify-center px-6 pb-20 pt-36 text-center sm:px-10 sm:pt-40 lg:px-16 lg:py-12 lg:text-left">
          <div className="mx-auto w-full max-w-[380px] lg:mx-0">
            <Brand />
            <div className="mt-6">
              <Title lead={lead} accent={accent} />
              <p className="mt-1.5 text-[15px] text-text/80">{sub}</p>
            </div>

            <form className="mt-6 space-y-3.5" onSubmit={submit}>
              {mode === 'signup' && (
                <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-2">
                  <Pill icon={UserRound} label="Your name" value={f.name} onChange={set('name')} required maxLength={40} autoComplete="name" />
                  <Pill icon={Store} label="Store name" value={f.store} onChange={set('store')} required maxLength={40} autoComplete="organization" />
                </div>
              )}
              {(mode === 'signin' || mode === 'signup' || mode === 'forgot') && (
                <Pill icon={Mail} label="Email address" type="email" value={f.email} onChange={set('email')} required autoComplete="email" />
              )}
              {codeStep && (
                <Pill
                  icon={KeyRound}
                  label="6-digit code"
                  value={f.code}
                  onChange={set('code')}
                  required
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  pattern="[0-9]{6}"
                  maxLength={6}
                  autoFocus
                />
              )}
              {(mode === 'signin' || mode === 'signup' || mode === 'reset') && (
                <PasswordPill
                  label={mode === 'reset' ? 'New password (8+ characters)' : mode === 'signup' ? 'Password (8+ characters)' : 'Password'}
                  value={f.password}
                  onChange={set('password')}
                  required
                  minLength={mode === 'signin' ? 1 : 8}
                  autoComplete={mode === 'signin' ? 'current-password' : 'new-password'}
                />
              )}

              {!accounts && <Note tone="warn">Accounts are offline right now. You can still try ShelfSense as a guest.</Note>}
              {signupPaused && <Note tone="warn">New accounts are paused (email is offline). Sign in or continue as a guest.</Note>}
              {info && <Note tone="info">{info}</Note>}
              {error && <Note tone="error">{error}</Note>}

              <Primary busy={busy} disabled={!accounts || signupPaused || (codeStep && f.code.length !== 6)}>
                {label[mode]}
              </Primary>
              {slow && (
                <p role="status" className="text-xs text-muted">
                  The free server is waking up — the first request can take up to a minute.
                </p>
              )}
            </form>

            {codeStep || mode === 'forgot' ? (
              <div className="mt-5 flex items-center justify-between text-sm">
                <button
                  type="button"
                  className="inline-flex items-center gap-1 font-semibold text-muted hover:text-text"
                  onClick={() => go(mode === 'verify' ? 'signup' : 'signin')}
                >
                  <ArrowLeft size={15} aria-hidden /> Back
                </button>
                {codeStep && (
                  <button type="button" className={`font-bold ${LINK} hover:underline disabled:opacity-50`} disabled={busy} onClick={() => void resend()}>
                    Send a new code
                  </button>
                )}
              </div>
            ) : (
              <div className="text-center">
                <div className="my-5 flex items-center gap-3 text-sm text-text/70" aria-hidden>
                  <span className="h-px flex-1 bg-[#D7E7DC] dark:bg-white/15" /> or <span className="h-px flex-1 bg-[#D7E7DC] dark:bg-white/15" />
                </div>
                <button
                  type="button"
                  onClick={continueAsGuest}
                  className="flex h-12 w-full items-center justify-center gap-2 rounded-full border-2 border-[#3DBE4F]/45 bg-white text-[15px] dark:bg-transparent font-bold text-text transition hover:border-[#3DBE4F] hover:bg-mint/60 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[#3DBE4F]/25"
                >
                  <UserRound size={18} aria-hidden /> Continue as guest <ArrowRight size={16} aria-hidden />
                </button>
                <p className="mt-2 text-xs text-muted">Guests get a fresh week in this tab; nothing is saved.</p>

                {mode === 'signin' && (
                  <button type="button" className={`mt-4 text-sm font-bold ${LINK} hover:underline`} onClick={() => go('forgot')}>
                    Forgot your password?
                  </button>
                )}
                <p className="mt-3 text-[15px] text-text/85">
                  {mode === 'signin' ? 'Don’t have an account?' : 'Already have an account?'}{' '}
                  <button type="button" className={`font-extrabold ${LINK} hover:underline`} onClick={() => go(mode === 'signin' ? 'signup' : 'signin')}>
                    {mode === 'signin' ? 'Sign Up' : 'Log In'}
                  </button>
                </p>
              </div>
            )}
          </div>
        </section>

        <PhotoPanel />
        <ThemeToggle className="absolute left-3 top-3 z-20 grid h-10 w-10 place-items-center rounded-full bg-panel/80 text-text shadow-sm backdrop-blur hover:bg-panel" />
      </main>
    </div>
  )
}
