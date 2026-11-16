/** The signed-in user's login token (localStorage, so it survives tabs and restarts). */
const KEY = 'shelfsense.token'

export function getToken(): string | null {
  try {
    return localStorage.getItem(KEY)
  } catch {
    return null
  }
}

export function setToken(t: string | null): void {
  try {
    if (t) localStorage.setItem(KEY, t)
    else localStorage.removeItem(KEY)
  } catch {
    // storage blocked: the sign-in lasts for this page load only
  }
}
