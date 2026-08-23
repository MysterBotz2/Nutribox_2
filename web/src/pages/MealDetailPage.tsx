import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { ApiError } from '../api/client'
import { mealsApi } from '../api/meals'
import { queryKeys } from '../api/query-keys'
import { LeftoverAnalysisPanel } from '../components/LeftoverAnalysisPanel'
import { NutrientTotals } from '../components/NutrientTotals'
import { StateMessage } from '../components/StateMessage'
import { formatLocalDateTime } from '../utils/date-time'
import { formatNutrient } from '../utils/format-nutrition'

export function MealDetailPage() {
  const parsedMealId = Number(useParams().mealId)
  const meal = useQuery({ queryKey: queryKeys.mealDetail(parsedMealId), queryFn: () => mealsApi.get(parsedMealId), enabled: Number.isInteger(parsedMealId) && parsedMealId > 0, retry: false })
  if (!Number.isInteger(parsedMealId) || parsedMealId <= 0 || (meal.error instanceof ApiError && meal.error.status === 404)) return <div className="page-stack"><StateMessage kind="error">Meal not found.</StateMessage><Link to="/app/meals">Back to meals</Link></div>
  if (meal.isPending) return <StateMessage>Loading meal…</StateMessage>
  if (meal.isError) return <StateMessage kind="error">Unable to load this meal. Please check your connection and try again.</StateMessage>
  return <div className="page-stack"><header className="page-header"><p className="eyebrow">Meal #{meal.data.id}</p><h1>Recorded meal</h1><p className="muted">{formatLocalDateTime(meal.data.recorded_at)}</p></header><section className="card"><h2>Stored totals</h2><NutrientTotals totals={meal.data.totals} /></section><LeftoverAnalysisPanel mealId={meal.data.id} /><section className="card"><h2>Stored meal items</h2><div className="meal-items">{meal.data.items.map((item) => <article className="meal-item" key={item.id}><h3>{item.food.name}</h3><p>{item.weight_grams} g portion</p><p>{formatNutrient('calories', item.nutrition.calories)} · Protein {formatNutrient('protein_g', item.nutrition.protein_g)}</p><NutrientTotals totals={item.nutrition} /></article>)}</div></section><Link to="/app/meals">Back to meals</Link></div>
}
