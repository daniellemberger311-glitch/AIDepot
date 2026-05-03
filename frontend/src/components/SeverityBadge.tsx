const MAP: Record<string, string> = {
  RED:    'bg-red-500/20 text-red-400 ring-red-500/30',
  YELLOW: 'bg-yellow-500/20 text-yellow-400 ring-yellow-500/30',
  GREEN:  'bg-emerald-500/20 text-emerald-400 ring-emerald-500/30',
}

export default function SeverityBadge({ severity }: { severity: string }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 text-xs font-semibold rounded-full ring-1 ${MAP[severity] ?? MAP.GREEN}`}>
      {severity}
    </span>
  )
}
