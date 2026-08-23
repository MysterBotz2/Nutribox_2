import type { WeightEntryList } from '../api/types'
import { formatLocalDateTime } from '../utils/date-time'

export function WeightHistoryChart({ entries }: WeightEntryList) {
  if (entries.length === 0) return <p className="muted">No weight entries have been recorded.</p>
  const points = [...entries].sort((a, b) => a.measured_at.localeCompare(b.measured_at)).map((entry) => ({ ...entry, value: Number(entry.weight_kg) }))
  if (points.some((point) => !Number.isFinite(point.value))) return <p className="state-message error">Unable to display weight chart data.</p>
  const min = Math.min(...points.map((point) => point.value)); const max = Math.max(...points.map((point) => point.value)); const range = Math.max(max - min, 0.1)
  return <div className="chart-wrap"><div className="bar-chart weight-chart" role="img" aria-label="Chronological weight history chart">{points.map((point) => <div className="chart-column" key={point.id}><div className="chart-bar" style={{ height: `${20 + ((point.value - min) / range) * 80}%` }} title={`${formatLocalDateTime(point.measured_at)}: ${point.weight_kg} kg`} /><span>{point.measured_at.slice(5, 10)}</span></div>)}</div><ul className="chart-values">{points.map((point) => <li key={point.id}><span>{formatLocalDateTime(point.measured_at)}</span><span>{point.weight_kg} kg</span></li>)}</ul></div>
}
