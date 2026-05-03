interface Props { value: number | null; suffix?: string }

export default function DeltaBadge({ value, suffix = '' }: Props) {
  if (value === null || value === undefined) return <span className="text-gray-600">–</span>
  const pos = value > 0
  const neu = value === 0
  return (
    <span className={`text-xs font-mono font-semibold ${neu ? 'text-gray-400' : pos ? 'text-emerald-400' : 'text-red-400'}`}>
      {pos ? '+' : ''}{value.toFixed(1)}{suffix}
    </span>
  )
}
