import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { mealsApi } from '../api/meals'
import { queryKeys } from '../api/query-keys'
import { StateMessage } from '../components/StateMessage'
import { formatLocalDateTime } from '../utils/date-time'
import { formatNutrient } from '../utils/format-nutrition'

const pageSize = 10
export function MealsPage() {
  const [offset, setOffset] = useState(0)
  const meals = useQuery({ queryKey: queryKeys.mealsList(pageSize, offset), queryFn: () => mealsApi.list(pageSize, offset) })
  if (meals.isPending) return <div className="dashboard-skeleton"><i /><i /><i /></div>
  if (meals.isError) return <StateMessage kind="error">Unable to load recorded meals. Please check your connection and try again.</StateMessage>
  return <div className="page-stack meals-page"><header className="dashboard-header"><div><p className="eyebrow">Meals</p><h1>Meal history</h1><p className="muted">Immutable meal and nutrition snapshots, newest first.</p></div><Link className="button-link" to="/app/scan">Analyze meal</Link></header>
    {meals.data.meals.length === 0 ? <StateMessage>No meals have been recorded yet.</StateMessage> : <div className="meal-list visual-meal-list">{meals.data.meals.map((meal) => <article className="card meal-card visual-meal-card" key={meal.id}><div className="meal-card-main"><p className="meal-time">{formatLocalDateTime(meal.recorded_at)}</p><h2>{meal.items.length} {meal.items.length === 1 ? 'item' : 'items'}</h2><p className="muted">Recorded meal #{meal.id} · stored nutrition snapshot</p><div className="meal-macros"><span className="calories">{formatNutrient('calories', meal.totals.calories)}</span><span className="protein">P {formatNutrient('protein_g', meal.totals.protein_g)}</span><span className="carbs">C {formatNutrient('carbohydrates_g', meal.totals.carbohydrates_g)}</span><span className="fat">F {formatNutrient('fat_g', meal.totals.fat_g)}</span><span className="fiber">Fiber {formatNutrient('fiber_g', meal.totals.fiber_g)}</span></div></div><Link className="text-action" to={`/app/meals/${meal.id}`}>View <span>→</span></Link></article>)}</div>}
    <nav className="pagination" aria-label="Meal history pagination"><button type="button" className="secondary-button" disabled={offset === 0} onClick={() => setOffset((current) => Math.max(0, current - pageSize))}>Previous</button><span>Showing meals starting at {offset + 1}</span><button type="button" disabled={meals.data.meals.length !== pageSize} onClick={() => setOffset((current) => current + pageSize)}>Next</button></nav></div>
}
