import { Loader2 } from 'lucide-react'
import { useT } from '../lib/i18n'

export default function WakingOverlay() {
  const t = useT()
  return (
    <div
      role="status"
      aria-live="polite"
      className="fixed inset-0 z-50 grid place-items-center bg-bg/90 backdrop-blur-sm"
    >
      <div className="max-w-sm rounded-lg border border-line bg-panel p-6 text-center">
        <Loader2 className="mx-auto mb-3 text-accent motion-safe:animate-spin" aria-hidden />
        <p className="font-medium">{t('Waking the simulation server…')}</p>
        <p className="mt-1 text-sm text-muted">
          {t('The free hosting tier sleeps when idle. This usually takes under a minute; the page reconnects on its own.')}
        </p>
      </div>
    </div>
  )
}
