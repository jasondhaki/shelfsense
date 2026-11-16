/** One simulation per browser tab: the id lives in sessionStorage (survives reloads, not tabs). */
const KEY = 'shelfsense-session'

function make(): string {
  return typeof crypto !== 'undefined' && 'randomUUID' in crypto
    ? crypto.randomUUID()
    : `s-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`
}

let cached: string | null = null

export function sessionId(): string {
  if (cached) return cached
  try {
    cached = sessionStorage.getItem(KEY) ?? make()
    sessionStorage.setItem(KEY, cached)
  } catch {
    cached = make() // storage blocked (private mode): still unique for this page load
  }
  return cached
}
