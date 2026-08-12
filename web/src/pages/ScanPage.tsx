import { useEffect, useState } from 'react'
import type { ChangeEvent, FormEvent } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'

import { ApiError } from '../api/client'
import { mealsApi } from '../api/meals'
import { queryKeys } from '../api/query-keys'
import { scanApi } from '../api/scan'
import type { MealAnalysisResponse } from '../api/types'
import { NutrientTotals } from '../components/NutrientTotals'
import { StateMessage } from '../components/StateMessage'

const supportedTypes = new Set(['image/jpeg', 'image/png', 'image/webp'])

function safeError(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.detail : fallback
}

export function ScanPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [file, setFile] = useState<File>()
  const [previewUrl, setPreviewUrl] = useState<string>()
  const [weightGrams, setWeightGrams] = useState('')
  const [analysis, setAnalysis] = useState<MealAnalysisResponse>()
  const [validationError, setValidationError] = useState<string>()
  useEffect(() => {
    if (!file) { setPreviewUrl(undefined); return }
    const url = URL.createObjectURL(file)
    setPreviewUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [file])
  const analyze = useMutation({ mutationFn: () => scanApi.analyze(file!, weightGrams), onSuccess: setAnalysis })
  const save = useMutation({
    mutationFn: () => {
      if (!analysis || analysis.status !== 'calculated') throw new Error('A calculated meal is required before saving.')
      return mealsApi.create({ items: [{ food_id: analysis.food.id, weight_grams: analysis.weight_grams }] })
    },
    onSuccess: (savedMeal) => {
      queryClient.invalidateQueries({ queryKey: ['meals'] })
      queryClient.invalidateQueries({ queryKey: ['progress'] })
      queryClient.removeQueries({ queryKey: queryKeys.scanAnalysis })
      navigate(`/app/meals/${savedMeal.id}`)
    },
  })
  function reset() { setFile(undefined); setWeightGrams(''); setAnalysis(undefined); setValidationError(undefined); analyze.reset(); save.reset() }
  function selectFile(event: ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files?.[0]
    if (!selected) return
    if (!supportedTypes.has(selected.type)) { setFile(undefined); setValidationError('Choose a JPEG, PNG, or WEBP image.'); return }
    setFile(selected); setAnalysis(undefined); setValidationError(undefined); analyze.reset(); save.reset()
  }
  function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); setValidationError(undefined); if (!file) { setValidationError('Choose an image before analyzing.'); return } if (!weightGrams) { setValidationError('Enter a manual portion weight in grams.'); return } analyze.mutate() }
  return <div className="page-stack"><header className="page-header"><p className="eyebrow">Scan Food</p><h1>Analyze a food image</h1><p className="muted">Web companion workflow: choose an image and enter a manual portion weight. This is not a physical-device scale workflow.</p></header>
    <form className="card scan-form" onSubmit={submit}><label htmlFor="scan-image">Food image<input id="scan-image" type="file" accept="image/jpeg,image/png,image/webp" capture="environment" onChange={selectFile} /></label><p className="muted">JPEG, PNG, or WEBP.</p>{previewUrl && <img className="scan-preview" src={previewUrl} alt="Selected food preview" />}
      <label htmlFor="scan-weight">Portion weight (grams)<input id="scan-weight" type="number" min="0" max="5000" step="any" value={weightGrams} onChange={(event) => setWeightGrams(event.target.value)} required /></label><p className="muted">Enter this manually; no device weight is used here.</p>
      {validationError && <StateMessage kind="error">{validationError}</StateMessage>}{analyze.isError && <StateMessage kind="error">{safeError(analyze.error, 'Unable to analyze this image.')}</StateMessage>}{save.isError && <StateMessage kind="error">{safeError(save.error, 'Unable to save this meal.')}</StateMessage>}
      <div className="inline-actions"><button type="submit" disabled={analyze.isPending || save.isPending}>{analyze.isPending ? 'Analyzing…' : 'Analyze image'}</button><button type="button" className="secondary-button" onClick={reset} disabled={analyze.isPending || save.isPending}>Start over</button></div>
    </form>
    {analysis && <AnalysisResult analysis={analysis} onReset={reset} onSave={() => { if (!save.isPending) save.mutate() }} isSaving={save.isPending} />}
  </div>
}

function AnalysisResult({ analysis, onReset, onSave, isSaving }: { analysis: MealAnalysisResponse; onReset: () => void; onSave: () => void; isSaving: boolean }) {
  if (analysis.status === 'calculated') return <section className="card result-card"><p className="eyebrow">Analysis complete</p><h2>{analysis.food.name}</h2><p>Recognition source: {analysis.recognition_source} · Manual weight: {analysis.weight_grams} g</p><p>Recognized: {analysis.recognized_foods.map((food) => food.name).join(', ') || 'None listed'}</p><NutrientTotals totals={analysis.nutrition} /><div className="inline-actions"><button type="button" onClick={onSave} disabled={isSaving}>{isSaving ? 'Saving meal…' : 'Confirm and save meal'}</button><button type="button" className="secondary-button" onClick={onReset} disabled={isSaving}>Start over</button></div></section>
  if (analysis.status === 'food_not_recognized') return <section className="card result-card"><h2>No identifiable food was recognized in this image.</h2><p>Recognition source: {analysis.recognition_source}</p><button type="button" onClick={onReset}>Try another image</button></section>
  if (analysis.status === 'nutrition_reference_not_found') return <section className="card result-card"><h2>Nutrition reference unavailable</h2><p>{analysis.recognized_foods.map((food) => food.name).join(', ') || 'The food'} was recognized, but a validated nutrition reference is not currently available.</p><p>Recognition source: {analysis.recognition_source}</p><button type="button" onClick={onReset}>Try another image</button></section>
  return <section className="card result-card"><h2>Individual food portions are required</h2><p>Multiple foods were recognized. Nutri-Box did not divide the supplied plate weight between them.</p><ul>{analysis.recognized_foods.map((food) => <li key={food.name}>{food.name}</li>)}</ul><p>Record individual food identity and portion weights in a future confirmation workflow.</p><button type="button" onClick={onReset}>Start over</button></section>
}
