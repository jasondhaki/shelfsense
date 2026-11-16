import type { ReactNode } from 'react'

/** Title row for a tab: heading and one line of context on the left, actions on the right. */
export default function PageHead({ title, lead, children }: { title: string; lead: string; children?: ReactNode }) {
  return (
    <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h2 className="text-xl font-extrabold tracking-tight">{title}</h2>
        <p className="max-w-[70ch] text-sm text-muted">{lead}</p>
      </div>
      {children && <div className="flex flex-wrap items-center gap-2">{children}</div>}
    </div>
  )
}
