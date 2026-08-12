import type { DailyProgressPoint } from '../api/types'
import { decimalStringToDisplayNumber } from '../utils/chart'
import { formatNutrient } from '../utils/format-nutrition'

export function DailyNutritionChart({ daily }: { daily: DailyProgressPoint[] }) {
  const points = daily.map((point) => ({ ...point, calories: decimalStringToDisplayNumber(point.totals.calories) }))
  if (points.some((point) => point.calories === null)) return <p className="state-message error">Unable to display calorie chart data.</p>
  const maximum = Math.max(1, ...points.map((point) => point.calories ?? 0))
  return <div className="chart-wrap"><div className="bar-chart" role="img" aria-label="Backend-provided daily calories chart">
    {points.map((point) => <div className="chart-column" key={point.date}><div className="chart-bar" style={{ height: `${((point.calories ?? 0) / maximum) * 100}%` }} title={`${point.date}: ${formatNutrient('calories', point.totals.calories)}`} /><span>{point.date.slice(5)}</span></div>)}
  </div><ul className="chart-values">{points.map((point) => <li key={point.date}><span>{point.date}</span><span>{formatNutrient('calories', point.totals.calories)} · {point.meal_count} meals</span></li>)}</ul></div>
}
