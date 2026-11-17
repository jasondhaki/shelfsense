import { createElement, Fragment, useCallback, type ReactNode } from 'react'
import { create } from 'zustand'
import { BN } from './bn'

/** English is the key; BN maps every key to Bengali. `t()` only accepts keys that exist in BN,
 *  so `npm run typecheck` fails on any UI string that has no translation. Text that comes from
 *  the server (agent reasoning, product names, error messages) stays as sent. */
export type Key = keyof typeof BN
export type Lang = 'en' | 'bn'
export type Vars = Record<string, string | number>
const KEY = 'shelfsense.lang'

function initial(): Lang {
  try {
    if (localStorage.getItem(KEY) === 'bn') return 'bn'
  } catch {
    // storage blocked: English
  }
  return 'en'
}

const apply = (l: Lang) => {
  document.documentElement.lang = l
}

export const useLang = create<{ lang: Lang; toggle: () => void }>((set, get) => ({
  lang: initial(),
  toggle: () => {
    const lang: Lang = get().lang === 'bn' ? 'en' : 'bn'
    try {
      localStorage.setItem(KEY, lang)
    } catch {
      // not remembered, still applied
    }
    apply(lang)
    set({ lang })
  },
}))
apply(useLang.getState().lang)

export function translate(lang: Lang, key: Key, vars?: Vars): string {
  const s: string = lang === 'bn' ? BN[key] : key
  return vars ? s.replace(/\{(\w+)\}/g, (m, k: string) => (k in vars ? String(vars[k]) : m)) : s
}

export type T = (key: Key, vars?: Vars) => string

export function useT(): T {
  const lang = useLang((s) => s.lang)
  return useCallback((key: Key, vars?: Vars) => translate(lang, key, vars), [lang])
}

/** For sentences with markup inside: `rich(t('Saved {kg} of waste'), { kg: <strong>…</strong> })`.
 *  The translation keeps the placeholder wherever Bengali word order puts it. */
export function rich(s: string, parts: Record<string, ReactNode>): ReactNode {
  return s.split(/(\{\w+\})/).map((piece, i) => {
    const k = /^\{(\w+)\}$/.exec(piece)?.[1]
    return createElement(Fragment, { key: i }, k && k in parts ? parts[k] : piece)
  })
}
