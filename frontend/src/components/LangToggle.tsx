import { Languages } from 'lucide-react'
import { useLang, useT } from '../lib/i18n'

/** EN ⇄ বাংলা. Shows the language you'd switch to, written in that language. */
export default function LangToggle({ className = 'flex h-11 items-center gap-1.5 rounded-full px-2.5 text-sm font-bold text-text hover:bg-panel' }: { className?: string }) {
  const lang = useLang((s) => s.lang)
  const toggle = useLang((s) => s.toggle)
  const t = useT()
  return (
    <button type="button" className={className} onClick={toggle} aria-label={t('Switch language')} title={t('Switch language')}>
      <Languages size={20} aria-hidden strokeWidth={1.8} />
      <span lang={lang === 'bn' ? 'en' : 'bn'}>{lang === 'bn' ? 'EN' : 'বাংলা'}</span>
    </button>
  )
}
