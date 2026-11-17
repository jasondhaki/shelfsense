import { AlertOctagon, CheckCircle2, Clock } from 'lucide-react'
import type { Severity } from '../types/contracts'
import type { Key } from './i18n'

/** Severity always carries an icon and words, never colour alone (FRONTEND §6). */
export const SEVERITY: Record<Severity, { label: Key; border: string; chip: string; Icon: typeof Clock }> = {
  optimal: { label: 'Optimal', border: 'border-ok', chip: 'bg-ok text-black', Icon: CheckCircle2 },
  accelerated_ripening: { label: 'Ripening fast', border: 'border-warn', chip: 'bg-warn text-black', Icon: Clock },
  clearance_required: { label: 'Clear now', border: 'border-crit', chip: 'bg-crit text-white', Icon: AlertOctagon },
}
