import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { mealsApi } from '../api/meals'
import { progressApi } from '../api/progress'
import { queryKeys } from '../api/query-keys'
import { CalorieRing } from '../components/CalorieRing'
import { MacroBar } from '../components/MacroBar'
import { StateMessage } from '../components/StateMessage'
import { formatNutrient, formatPercent } from '../utils/format-nutrition'
import { getBrowserTimezone } from '../utils/timezone'

const timezone = getBrowserTimezone()
const greeting = () => new Date().getHours() < 12 ? 'Good morning' : new Date().getHours() < 18 ? 'Good afternoon' : 'Good evening'

export function DashboardPage() {
  const today = useQuery({ queryKey: queryKeys.todayProgress(timezone), queryFn: () => progressApi.getToday(timezone) })
  const targetStatus = useQuery({ queryKey: queryKeys.targetStatus(timezone), queryFn: () => progressApi.getTargetStatus(timezone) })
  const recentMeals = useQuery({ queryKey: queryKeys.recentMeals, queryFn: () => mealsApi.listRecent() })
  if (today.isPending || targetStatus.isPending) return <div className="dashboard-skeleton"><i /><i /><i /></div>
  if (today.isError || targetStatus.isError) return <StateMessage kind="error">Unable to load your dashboard. Please check your connection and try again.</StateMessage>
  const status = targetStatus.data
  const dateLabel = new Intl.DateTimeFormat(undefined, { weekday: 'long', month: 'long', day: 'numeric' }).format(new Date())
  return <div className="page-stack dashboard-page"><header className="dashboard-header"><div><p className="eyebrow">Home</p><h1>{greeting()}</h1><h2 className="sr-only">Today’s recorded nutrition</h2><p className="muted">{dateLabel}</p></div><Link className="button-link" to="/app/ai/coach">View Coaching</Link></header>
    <div className="dashboard-primary"><section className="card today-nutrition-card"><div><p className="eyebrow">Today’s Nutrition</p><h2>{today.data.meal_count} {today.data.meal_count === 1 ? 'meal' : 'meals'} logged</h2>{today.data.meal_count === 0 ? <StateMessage>No meals recorded for this date.</StateMessage> : <div className="macro-bars"><MacroBar nutrient="protein_g" value={today.data.totals.protein_g} target={status.targets?.protein_g} /><MacroBar nutrient="carbohydrates_g" value={today.data.totals.carbohydrates_g} target={status.targets?.carbohydrates_g} /><MacroBar nutrient="fat_g" value={today.data.totals.fat_g} target={status.targets?.fat_g} /></div>}</div><CalorieRing calories={today.data.totals.calories} target={status.targets?.calories} /></section><section className="card coach-preview-card"><p className="eyebrow">AI Coach</p><h2>Guidance that starts with your records.</h2><p className="muted">Review today’s meal logging and configured targets with your NutriBox coach.</p><Link className="text-action" to="/app/ai/coach">Open coaching <span>→</span></Link></section></div>
    <div className="metric-card-grid"><article className="metric-card"><span>Meals Today</span><strong>{today.data.meal_count}</strong><small>Recorded meals</small></article><article className="metric-card"><span>Nutrition Target</span><strong>{status.targets?.calories ? formatPercent(status.percent_of_target?.calories) : '—'}</strong><small>{status.targets?.calories ? 'Calorie target used' : 'No target configured'}</small></article><article className="metric-card"><span>Fiber</span><strong>{formatNutrient('fiber_g', today.data.totals.fiber_g)}</strong><small>Recorded today</small></article></div>
    {status.targets ? <>{status.remaining?.calories?.startsWith('-') && <span className="sr-only">Above configured target by {formatNutrient('calories', status.remaining.calories.slice(1))}</span>}</> : <span className="sr-only">No nutrition targets configured.</span>}
    <section className="card recent-meals-card"><div className="section-heading"><div><p className="eyebrow">Meal history</p><h2>Recent Meals</h2></div><Link className="text-action" to="/app/meals">View all <span>→</span></Link></div>{recentMeals.isPending ? <StateMessage>Loading recent meals…</StateMessage> : recentMeals.isError ? <StateMessage kind="error">Unable to load recent meals.</StateMessage> : recentMeals.data?.meals.length === 0 ? <StateMessage>No meals have been recorded yet.</StateMessage> : <ul className="recent-meals">{recentMeals.data?.meals.map((meal) => <li key={meal.id}><div><strong>{meal.items.length} {meal.items.length === 1 ? 'food item' : 'food items'}</strong><span>{new Date(meal.recorded_at).toLocaleString()}</span></div><strong className="numeric">{formatNutrient('calories', meal.totals.calories)}</strong></li>)}</ul>}</section>
  </div>
}
