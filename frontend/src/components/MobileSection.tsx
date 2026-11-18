import { ArrowRight, ChevronDown, type LucideIcon } from 'lucide-react'
import { useId, useState, type ReactNode } from 'react'
import { useT } from '../lib/i18n'
import { useMedia } from '../lib/useMedia'

interface Props {
  title: string
  Icon: LucideIcon
  link?: { label: string; onClick: () => void }
  defaultOpen?: boolean
  /** One `.zone` card; its own first row (title + link) is hidden here, the header replaces it. */
  children: ReactNode
}

/** Phones: a card that folds to its title row. Desktop: just the card. */
export default function MobileSection({ title, Icon, link, defaultOpen = false, children }: Props) {
  const desktop = useMedia('(min-width: 1024px)')
  const [open, setOpen] = useState(defaultOpen)
  const id = useId()
  const t = useT()
  if (desktop) return <>{children}</>
  return (
    <div className="zone">
      <div className="flex items-center gap-2 px-4 py-3.5">
        <button
          type="button"
          aria-expanded={open}
          aria-controls={id}
          aria-label={t(open ? 'Hide {section}' : 'Show {section}', { section: title })}
          onClick={() => setOpen(!open)}
          className="flex min-w-0 flex-1 items-center gap-3 text-left"
        >
          <Icon size={24} aria-hidden strokeWidth={1.8} className="shrink-0 text-accent" />
          <span className="truncate text-[15px] font-bold tracking-tight">{title}</span>
        </button>
        {link && (
          <button type="button" className="link shrink-0 text-sm" onClick={link.onClick}>
            {link.label} <ArrowRight size={14} aria-hidden />
          </button>
        )}
        <button type="button" tabIndex={-1} aria-hidden onClick={() => setOpen(!open)} className="grid h-8 w-8 shrink-0 place-items-center text-muted">
          <ChevronDown size={20} className={`transition-transform ${open ? 'rotate-180' : ''}`} />
        </button>
      </div>
      <div
        id={id}
        hidden={!open}
        className="[&>.zone]:rounded-none [&>.zone]:border-0 [&>.zone]:bg-transparent [&>.zone]:pt-0 [&>.zone]:shadow-none [&>.zone>*:first-child]:hidden"
      >
        {children}
      </div>
    </div>
  )
}
