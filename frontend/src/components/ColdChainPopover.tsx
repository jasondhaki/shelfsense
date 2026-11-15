import { Snowflake } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import type { EslView } from '../types/contracts'

const DEFAULT_SKUS = ['STRW-01', 'SPIN-01', 'SALM-01']

interface Props {
  skus: EslView[]
  pending: boolean
  disabled: boolean
  onTrigger: (skus: string[], immediate: boolean) => void
}

export default function ColdChainPopover({ skus, pending, disabled, onTrigger }: Props) {
  const [open, setOpen] = useState(false)
  const [picked, setPicked] = useState<string[]>(DEFAULT_SKUS)
  const [immediate, setImmediate] = useState(false)
  const root = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const onDown = (e: MouseEvent) => {
      if (!root.current?.contains(e.target as Node)) setOpen(false)
    }
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false)
    document.addEventListener('mousedown', onDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  const toggle = (id: string) =>
    setPicked((p) => (p.includes(id) ? p.filter((x) => x !== id) : [...p, id]))

  return (
    <div ref={root} className="relative">
      <button
        type="button"
        aria-expanded={open}
        aria-haspopup="dialog"
        disabled={disabled || pending}
        onClick={() => setOpen((o) => !o)}
        className="btn"
      >
        <Snowflake size={14} aria-hidden />
        {pending ? 'Cold-chain: next delivery' : 'Cold-chain delay'}
      </button>
      {open && (
        <div
          role="dialog"
          aria-label="Cold-chain delay"
          className="absolute right-0 top-full z-30 mt-1 w-64 rounded-md border border-line bg-panel-2 p-3 shadow-xl"
        >
          <p className="mb-2 text-xs text-muted">
            Affected deliveries arrive with 30% less shelf life, in both stores.
          </p>
          <fieldset className="mb-2 grid grid-cols-2 gap-x-2 gap-y-1">
            <legend className="sr-only">Products</legend>
            {skus.map((s) => (
              <label key={s.sku_id} className="flex items-center gap-1.5 text-xs">
                <input
                  type="checkbox"
                  checked={picked.includes(s.sku_id)}
                  onChange={() => toggle(s.sku_id)}
                  className="accent-accent"
                />
                <span className="truncate" title={s.name}>
                  {s.name.split(' ').slice(0, 2).join(' ')}
                </span>
              </label>
            ))}
          </fieldset>
          <fieldset className="mb-3 flex gap-3 text-xs">
            <legend className="sr-only">When</legend>
            <label className="flex items-center gap-1.5">
              <input
                type="radio"
                name="cc-when"
                checked={!immediate}
                onChange={() => setImmediate(false)}
                className="accent-accent"
              />
              Next delivery
            </label>
            <label className="flex items-center gap-1.5">
              <input
                type="radio"
                name="cc-when"
                checked={immediate}
                onChange={() => setImmediate(true)}
                className="accent-accent"
              />
              Deliver now
            </label>
          </fieldset>
          <button
            type="button"
            disabled={picked.length === 0}
            onClick={() => {
              onTrigger(picked, immediate)
              setOpen(false)
            }}
            className="btn w-full justify-center"
          >
            Apply delay to {picked.length} product{picked.length === 1 ? '' : 's'}
          </button>
        </div>
      )}
    </div>
  )
}
