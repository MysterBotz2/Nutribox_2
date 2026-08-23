import { useState } from 'react'
import type { FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ApiError } from '../api/client'
import { mealsApi } from '../api/meals'
import { queryKeys } from '../api/query-keys'
import { NutrientTotals } from './NutrientTotals'
import { StateMessage } from './StateMessage'

export function LeftoverAnalysisPanel({ mealId }: { mealId: number }) {
  const queryClient = useQueryClient(); const [weight, setWeight] = useState('0'); const [image, setImage] = useState<File | null>(null)
  const analysis = useQuery({ queryKey: queryKeys.leftoverAnalysis(mealId), queryFn: () => mealsApi.getLeftoverAnalysis(mealId), retry: false })
  const absent = analysis.error instanceof ApiError && analysis.error.status === 404
  const create = useMutation({ mutationFn: () => { const data = new FormData(); data.set('leftover_weight_grams', weight); if (image) data.set('file', image); return mealsApi.createLeftoverAnalysis(mealId, data) }, onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.leftoverAnalysis(mealId) }) })
  function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); if (Number(weight) > 0 && !image) return; create.mutate() }
  if (analysis.isPending) return <section className="card"><StateMessage>Loading leftover analysis…</StateMessage></section>
  if (analysis.isError && !absent) return <section className="card"><StateMessage kind="error">Unable to load leftover analysis.</StateMessage></section>
  if (analysis.data) return <section className="card"><h2>Leftover analysis</h2><p className="muted">Saved from {analysis.data.leftover_weight_grams} g leftover measurement.</p><h3>Initial Nutrition</h3><NutrientTotals totals={analysis.data.initial_nutrition} /><h3>Leftover Nutrition</h3><NutrientTotals totals={analysis.data.leftover_nutrition} /><h3>Consumed Nutrition</h3><NutrientTotals totals={analysis.data.consumed_nutrition} /></section>
  const positiveWeightNeedsImage = Number(weight) > 0 && !image
  return <section className="card"><h2>Leftover analysis</h2><p className="muted">Compare this meal’s stored nutrition with the leftover portion. A 0 g leftover needs no image.</p><form onSubmit={submit}><label>Leftover weight (g)<input type="number" min="0" step="0.001" required value={weight} onChange={(event) => setWeight(event.target.value)} /></label><label>Leftover image {Number(weight) > 0 && <span className="muted">(required above 0 g)</span>}<input type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => setImage(event.target.files?.[0] ?? null)} /></label>{positiveWeightNeedsImage && <StateMessage kind="error">An image is required when leftover weight is above 0 g.</StateMessage>}{create.isError && <StateMessage kind="error">{create.error instanceof ApiError && create.error.status === 409 ? 'A finalized leftover analysis already exists for this meal.' : create.error instanceof ApiError ? create.error.detail : 'Unable to analyze leftovers.'}</StateMessage>}<button type="submit" disabled={create.isPending || positiveWeightNeedsImage}>{create.isPending ? 'Analyzing…' : 'Save leftover analysis'}</button></form></section>
}
