const ZONE_STYLES: Record<number, string> = {
  1: 'bg-emerald-500/20 text-emerald-400 ring-emerald-500/30',
  2: 'bg-yellow-500/20 text-yellow-400 ring-yellow-500/30',
  3: 'bg-orange-500/20 text-orange-400 ring-orange-500/30',
  4: 'bg-gray-500/20 text-gray-400 ring-gray-500/30',
}

export const ZONE_COLORS: Record<number, string> = {
  1: '#10b981', 2: '#eab308', 3: '#f97316', 4: '#6b7280',
}

export default function ZoneBadge({ zone }: { zone: number }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 text-xs font-semibold rounded-full ring-1 ${ZONE_STYLES[zone] ?? ZONE_STYLES[4]}`}>
      Z{zone}
    </span>
  )
}
