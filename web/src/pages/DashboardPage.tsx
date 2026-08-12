import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { mealsApi } from '../api/meals'
import { progressApi } from '../api/progress'
import { queryKeys } from '../api/query-keys'
import { NutrientTotals } from '../components/NutrientTotals'
import { StateMessage } from '../components/StateMessage'
import { formatNutrient, formatPercent, nutrientLabels, type NutrientKey } from '../utils/format-nutrition'
import { getBrowserTimezone } from '../utils/timezone'

const timezone = getBrowserTimezone()
const nutrientKeys: NutrientKey[] = ['calories', 'protein_g', 'carbohydrates_g', 'fat_g', 'fiber_g']

function displayRemaining(key: NutrientKey, value: string | null | undefined): string {
  if (value === null || value === undefined) return 'Not configured'
  if (value.startsWith('-')) return `Above configured target by ${formatNutrient(key, value.slice(1))}`
  return `${formatNutrient(key, value)} remaining`
}

export function DashboardPage() {
  const today = useQuery({ queryKey: queryKeys.todayProgress(timezone), queryFn: () => progressApi.getToday(timezone) })
  const targetStatus = useQuery({ queryKey: queryKeys.targetStatus(timezone), queryFn: () => progressApi.getTargetStatus(timezone) })
  const recentMeals = useQuery({ queryKey: queryKeys.recentMeals, queryFn: () => mealsApi.listRecent() })

  if (today.isPending || targetStatus.isPending) return <StateMessage>Loading today’s recorded nutrition…</StateMessage>
  if (today.isError || targetStatus.isError) return <StateMessage kind="error">Unable to load dashboard data. Please check your connection and try again.</StateMessage>

  const status = targetStatus.data
  return <div className="page-stack"><header className="page-header"><p className="eyebrow">Dashboard</p><h1>Today’s recorded nutrition</h1><p className="muted">{today.data.date} · {timezone}</p></header>
    <section className="card"><div className="section-heading"><div><h2>Today</h2><p>{today.data.meal_count} {today.data.meal_count === 1 ? 'meal' : 'meals'} recorded</p></div></div>
      {today.data.meal_count === 0 && <StateMessage>No meals recorded for this date.</StateMessage>}
      <NutrientTotals totals={today.data.totals} />
    </section>
    <section className="card"><div className="section-heading"><div><h2>Configured target comparison</h2><p>Neutral comparison using your configured targets.</p></div>{!status.targets && <Link className="button-link" to="/app/targets">Configure targets</Link>}</div>
      {!status.targets ? <StateMessage>No nutrition targets configured.</StateMessage> : <div className="target-list">{nutrientKeys.filter((key) => status.targets?.[key] !== null && status.targets?.[key] !== undefined).map((key) => {
        const percent = status.percent_of_target?.[key]
        const fill = percent === null || percent === undefined ? 0 : Math.min(100, Math.max(0, Number(percent)))
        return <article className="target-row" key={key}><div className="target-row-heading"><h3>{nutrientLabels[key]}</h3><strong>{formatPercent(percent)}</strong></div><p>Consumed: {formatNutrient(key, status.consumed[key])} · Target: {formatNutrient(key, status.targets?.[key])}</p><p>{displayRemaining(key, status.remaining?.[key])}</p><div className="progress-track" aria-label={`${nutrientLabels[key]} progress`}><div className="progress-fill" style={{ width: `${fill}%` }} /></div></article>
      })}</div>}
    </section>
    <section className="card"><div className="section-heading"><div><h2>Recent meals</h2><p>A small view of the most recently recorded meals.</p></div></div>
      {recentMeals.isPending && <StateMessage>Loading recent meals…</StateMessage>}
      {recentMeals.isError && <StateMessage kind="error">Unable to load recent meals.</StateMessage>}
      {recentMeals.data?.meals.length === 0 && <StateMessage>No recorded meals yet.</StateMessage>}
      {recentMeals.data && recentMeals.data.meals.length > 0 && <ul className="recent-meals">{recentMeals.data.meals.map((meal) => <li key={meal.id}><div><strong>{new Date(meal.recorded_at).toLocaleString()}</strong><span>{meal.items.length} {meal.items.length === 1 ? 'item' : 'items'}</span></div><strong>{formatNutrient('calories', meal.totals.calories)}</strong></li>)}</ul>}
    </section>
  </div>
}
