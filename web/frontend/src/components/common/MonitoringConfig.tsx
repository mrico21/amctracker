import { useState } from 'react'
import type { WatchlistAdjacentConfig } from '@/api/types'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

// ── Seat badge ────────────────────────────────────────────────────────────────

function SeatBadge({ label }: { label: string }) {
  return (
    <Badge variant="secondary" className="font-mono text-xs">
      {label}
    </Badge>
  )
}

// ── Collapsible seat list ─────────────────────────────────────────────────────

const SEAT_COLLAPSE_THRESHOLD = 8
const SEAT_VISIBLE_COUNT = 6

function SeatList({ seats, defaultExpanded = false }: { seats: string[]; defaultExpanded?: boolean }) {
  const [expanded, setExpanded] = useState(defaultExpanded)
  const collapsible = seats.length > SEAT_COLLAPSE_THRESHOLD

  const visible = collapsible && !expanded ? seats.slice(0, SEAT_VISIBLE_COUNT) : seats
  const hiddenCount = seats.length - visible.length

  return (
    <span className="flex flex-wrap items-center gap-1">
      {visible.map((seat) => (
        <SeatBadge key={seat} label={seat} />
      ))}
      {collapsible && !expanded && (
        <button
          onClick={() => setExpanded(true)}
          className="text-xs text-muted-foreground hover:text-foreground underline-offset-2 hover:underline transition-colors"
        >
          +{hiddenCount} more
        </button>
      )}
      {collapsible && expanded && (
        <button
          onClick={() => setExpanded(false)}
          className="text-xs text-muted-foreground hover:text-foreground underline-offset-2 hover:underline transition-colors"
        >
          show fewer
        </button>
      )}
    </span>
  )
}

// ── Adjacent config row ───────────────────────────────────────────────────────

function AdjacentRow({ cfg }: { cfg: WatchlistAdjacentConfig }) {
  return (
    <div className="flex flex-wrap items-center gap-1">
      <span className="text-xs text-muted-foreground">
        Adjacent {cfg.count} in:
      </span>
      {cfg.rows.map((row) => (
        <SeatBadge key={row} label={`Row ${row}`} />
      ))}
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

interface MonitoringConfigProps {
  watch_seats: string[]
  watch_any: string[]
  watch_adjacent: WatchlistAdjacentConfig[]
  /** Show an explicit section label above the config */
  showLabel?: boolean
  /** When true, seat lists start expanded regardless of count */
  defaultExpanded?: boolean
  className?: string
}

export function MonitoringConfig({
  watch_seats,
  watch_any,
  watch_adjacent,
  showLabel = false,
  defaultExpanded = false,
  className,
}: MonitoringConfigProps) {
  const hasSeats = watch_seats.length > 0
  const hasAny = watch_any.length > 0
  const hasAdjacent = watch_adjacent.length > 0

  if (!hasSeats && !hasAny && !hasAdjacent) return null

  return (
    <div className={cn('space-y-1.5', className)}>
      {showLabel && (
        <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          Monitoring
        </p>
      )}

      {hasSeats && (
        <div className="flex flex-wrap items-start gap-1">
          <span className="mt-0.5 flex-shrink-0 text-xs text-muted-foreground">Specific seats:</span>
          <SeatList seats={watch_seats} defaultExpanded={defaultExpanded} />
        </div>
      )}

      {hasAny && (
        <div className="flex flex-wrap items-start gap-1">
          <span className="mt-0.5 flex-shrink-0 text-xs text-muted-foreground">Any seat in:</span>
          <SeatList seats={watch_any} defaultExpanded={defaultExpanded} />
        </div>
      )}

      {hasAdjacent && watch_adjacent.map((cfg, i) => <AdjacentRow key={i} cfg={cfg} />)}
    </div>
  )
}
