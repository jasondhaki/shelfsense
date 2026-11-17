import {
  BarChart3,
  Boxes,
  CircleHelp,
  Database,
  Home,
  PieChart,
  Settings,
  ShoppingCart,
  Sparkles,
  Tag,
  type LucideIcon,
} from 'lucide-react'
import type { Key } from '../lib/i18n'
import type { Page } from '../store/simStore'

export const NAV: { id: Page; label: Key; Icon: LucideIcon }[] = [
  { id: 'dashboard', label: 'Dashboard', Icon: Home },
  { id: 'inventory', label: 'Inventory', Icon: Boxes },
  { id: 'forecast', label: 'Forecast', Icon: BarChart3 },
  { id: 'pricing', label: 'Pricing & Discounts', Icon: Tag },
  { id: 'agents', label: 'AI Agents', Icon: Sparkles },
  { id: 'orders', label: 'Orders', Icon: ShoppingCart },
  { id: 'analytics', label: 'Analytics', Icon: PieChart },
  { id: 'data', label: 'Data Ingestion', Icon: Database },
]
export const FOOT: typeof NAV = [
  { id: 'settings', label: 'Settings', Icon: Settings },
  { id: 'help', label: 'Help', Icon: CircleHelp },
]

