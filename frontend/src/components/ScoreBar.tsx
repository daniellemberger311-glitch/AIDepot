import { ZONE_COLORS } from './ZoneBadge'

interface Props {
  score: number
  zone: number
  showLabel?: boolean
}

export default function ScoreBar({ score, zone, showLabel = true }: Props) {
  const color = ZONE_COLORS[zone] ?? ZONE_COLORS[4]
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${Math.min(score, 100)}%`, background: color }}
        />
      </div>
      {showLabel && (
        <span className="text-xs font-mono font-semibold w-8 text-right" style={{ color }}>
          {score.toFixed(0)}
        </span>
      )}
    </div>
  )
}
