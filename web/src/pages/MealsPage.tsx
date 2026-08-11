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
  if (meals.isPending) return <StateMessage>Loading recorded meals…</StateMessage>
  if (meals.isError) return <StateMessage kind="error">Unable to load recorded meals. Please check your connection and try again.</StateMessage>
  const hasNext = meals.data.meals.length === pageSize
  return <div className="page-stack"><header className="page-header"><p className="eyebrow">Meals</p><h1>Meal history</h1><p className="muted">Stored historical meal snapshots, newest first.</p></header>
    {meals.data.meals.length === 0 ? <StateMessage>No meals have been recorded yet.</StateMessage> : <div className="meal-list">{meals.data.meals.map((meal) => <article className="card meal-card" key={meal.id}><div><p className="muted">Meal #{meal.id} · {formatLocalDateTime(meal.recorded_at)}</p><h2>{meal.items.length} {meal.items.length === 1 ? 'item' : 'items'}</h2><p>{formatNutrient('calories', meal.totals.calories)} · Protein {formatNutrient('protein_g', meal.totals.protein_g)}</p></div><Link className="button-link" to={`/app/meals/${meal.id}`}>View meal</Link></article>)}</div>}
    <nav className="pagination" aria-label="Meal history pagination"><button type="button" className="secondary-button" disabled={offset === 0} onClick={() => setOffset((current) => Math.max(0, current - pageSize))}>Previous</button><span>Showing meals starting at {offset + 1}</span><button type="button" disabled={!hasNext} onClick={() => setOffset((current) => current + pageSize)}>Next</button></nav>
  </div>
}
