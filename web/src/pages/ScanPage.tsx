import { useEffect, useRef, useState } from 'react'
import type { ChangeEvent, FormEvent } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ApiError } from '../api/client'
import { mealsApi } from '../api/meals'
import { scanApi } from '../api/scan'
import type { MealAnalysisComponentResponse, MealAnalysisResponse } from '../api/types'
import { NutrientTotals } from '../components/NutrientTotals'
import { StateMessage } from '../components/StateMessage'

const supportedTypes = new Set(['image/jpeg', 'image/png', 'image/webp'])
const maxWeightGrams = 5000
const safeError = (error: unknown, fallback: string) => error instanceof ApiError ? error.detail : fallback

function isValidWeight(value: string): boolean {
  if (!value.trim()) return false
  const parsed = Number(value)
  return Number.isFinite(parsed) && parsed >= 0 && parsed <= maxWeightGrams
}

export function ScanPage() {
  const queryClient = useQueryClient()
  const uploadInput = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File>()
  const [previewUrl, setPreviewUrl] = useState<string>()
  const [weight, setWeight] = useState('')
  const [analysis, setAnalysis] = useState<MealAnalysisResponse>()
  const [validation, setValidation] = useState<string>()
  const [success, setSuccess] = useState<string>()

  useEffect(() => {
    if (!file) {
      setPreviewUrl(undefined)
      return
    }
    const url = URL.createObjectURL(file)
    setPreviewUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [file])

  const analyze = useMutation({
    mutationFn: () => scanApi.analyze(file!, weight),
    onSuccess: result => { setAnalysis(result); setSuccess(undefined) },
  })
  const select = useMutation({
    mutationFn: ({ sessionId, componentId, candidateId }: { sessionId: number; componentId: string; candidateId: string }) => scanApi.selectCandidate(sessionId, { component_id: componentId, candidate_id: candidateId }),
    onSuccess: setAnalysis,
  })
  const save = useMutation({
    mutationFn: () => {
      if (!analysis || analysis.status !== 'calculated') throw new Error('A calculated analysis is required.')
      return analysis.analysis_session_id
        ? mealsApi.create({ analysis_session_id: analysis.analysis_session_id })
        : mealsApi.create({ items: [{ food_id: analysis.food!.id, weight_grams: analysis.weight_grams }] })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['meals'] })
      queryClient.invalidateQueries({ queryKey: ['progress'] })
      clearScan()
      setSuccess('Meal logged successfully.')
    },
  })

  const busy = analyze.isPending || select.isPending || save.isPending
  const canAnalyze = Boolean(file) && isValidWeight(weight) && !busy

  function clearScan() {
    setFile(undefined); setWeight(''); setAnalysis(undefined); setValidation(undefined)
    analyze.reset(); select.reset(); save.reset()
  }
  function clearImage() { setFile(undefined); setAnalysis(undefined); setValidation(undefined) }
  function choose(event: ChangeEvent<HTMLInputElement>) {
    const chosen = event.target.files?.[0]
    event.target.value = ''
    if (!chosen) return
    if (!supportedTypes.has(chosen.type)) { setValidation('Choose a JPEG, PNG, or WEBP image.'); return }
    setFile(chosen); setAnalysis(undefined); setValidation(undefined); setSuccess(undefined)
  }
  function submit(event: FormEvent) {
    event.preventDefault()
    if (!file || !isValidWeight(weight)) {
      setValidation(!file ? 'Choose an image before analyzing.' : `Enter a meal weight from 0 to ${maxWeightGrams} g.`)
      return
    }
    setValidation(undefined); analyze.mutate()
  }
  const error = select.error ?? save.error ?? analyze.error

  return <div className="page-stack scan-page"><header className="page-header"><p className="eyebrow">Scan meal</p><h1>Analyze a full meal</h1><p className="muted">Use this browser test client to analyze a food image before NutriBox Pi capture is available.</p></header><form className="card scan-form" onSubmit={submit}><fieldset className="scan-image-picker"><legend>Food image</legend><input id="scan-photo" className="visually-hidden" type="file" accept="image/*" capture="environment" onChange={choose} /><input id="scan-upload" ref={uploadInput} className="visually-hidden" type="file" accept="image/*" onChange={choose} />{!previewUrl ? <div className="inline-actions scan-picker-actions"><label className="secondary-button" htmlFor="scan-photo">Take photo</label><label className="secondary-button" htmlFor="scan-upload">Upload image</label></div> : <div className="scan-preview-wrap"><img className="scan-preview" src={previewUrl} alt="Selected food preview" /><div className="inline-actions scan-picker-actions"><button className="secondary-button" type="button" onClick={() => uploadInput.current?.click()} disabled={busy}>Replace image</button><button className="secondary-button" type="button" onClick={clearImage} disabled={busy}>Clear image</button></div></div>}</fieldset><label htmlFor="scan-weight">Meal weight (g)<input id="scan-weight" type="number" min="0" max={maxWeightGrams} step="0.001" required value={weight} onChange={event => setWeight(event.target.value)} /></label><p className="muted">Enter the total food weight for this test scan. On the NutriBox device, this will be supplied automatically by the scale.</p>{validation && <StateMessage kind="error">{validation}</StateMessage>}{error && <StateMessage kind="error">{error instanceof ApiError && error.status === 410 ? 'This meal analysis has expired. Please scan the meal again.' : error instanceof ApiError && error.status === 409 ? 'This analysis was already used or is not ready to log.' : safeError(error, 'Unable to complete meal analysis.')}</StateMessage>}{success && <StateMessage kind="success">{success}</StateMessage>}<div className="inline-actions"><button disabled={!canAnalyze}>{analyze.isPending ? 'Analyzing meal…' : 'Analyze meal'}</button><button className="secondary-button" type="button" onClick={clearScan} disabled={busy}>Start over</button></div></form>{analysis && <AnalysisResult analysis={analysis} selecting={select.isPending} saving={save.isPending} onReset={clearScan} onSave={() => save.mutate()} onSelect={(componentId, candidateId) => analysis.analysis_session_id && select.mutate({ sessionId: analysis.analysis_session_id, componentId, candidateId })} />}</div>
}

function ComponentCard({ component, selecting, onSelect }: { component: MealAnalysisComponentResponse; selecting: boolean; onSelect: (componentId: string, candidateId: string) => void }) {
  const [candidate, setCandidate] = useState('')
  const state = component.resolution_status
  return <article className="meal-item"><div className="section-heading"><div><h3>{component.recognized_name}</h3><p className="numeric">~{component.estimated_weight_grams} g</p><p className="muted">Estimated component portion</p></div><span className="badge">{state === 'resolved' ? 'Resolved' : state === 'requires_food_selection' ? 'Needs confirmation' : 'Nutrition reference unavailable'}</span></div>{component.nutrition_source === 'ai_recipe_estimate' ? <><p className="muted">Nutrition source: Estimated from dish composition</p><p className="muted">Ingredient proportions were estimated because an exact prepared-food reference was unavailable.</p></> : component.nutrition_source && <p className="muted">Nutrition source: {component.nutrition_source}</p>}{component.nutrition && <NutrientTotals totals={component.nutrition} />}{state === 'requires_food_selection' && <fieldset><legend>Choose the closest nutrition reference</legend>{component.candidates.map(item => <label key={item.candidate_id ?? item.name}><input type="radio" name={component.component_id} checked={candidate === item.candidate_id} onChange={() => setCandidate(item.candidate_id ?? '')} /> {item.name}</label>)}<button type="button" disabled={!candidate || selecting} onClick={() => onSelect(component.component_id, candidate)}>{selecting ? 'Updating nutrition reference…' : 'Confirm selection'}</button></fieldset>}</article>
}

function AnalysisResult({ analysis, selecting, saving, onSelect, onSave, onReset }: { analysis: MealAnalysisResponse; selecting: boolean; saving: boolean; onSelect: (id: string, candidate: string) => void; onSave: () => void; onReset: () => void }) {
  if (analysis.status === 'food_not_recognized') return <section className="card result-card"><h2>No identifiable food was recognized in this image.</h2><button onClick={onReset}>Try another photo</button></section>
  const components = analysis.components ?? []
  if (components.length === 0 && analysis.status === 'nutrition_reference_not_found') return <section className="card result-card"><h2>Nutrition reference unavailable</h2><p>{analysis.recognized_foods.map(food => food.name).join(', ') || 'The food'} was recognized, but a validated nutrition reference is not currently available.</p><button onClick={onReset}>Try another photo</button></section>
  if (components.length === 0 && analysis.status === 'requires_food_selection') return <section className="card result-card"><h2>Individual food portions are required</h2><p>Multiple foods were recognized. Nutri-Box did not divide the supplied plate weight between them.</p><button onClick={onReset}>Start over</button></section>
  const measuredWeight = analysis.measured_weight_grams ?? ('weight_grams' in analysis ? analysis.weight_grams : '—')
  return <div className="page-stack"><section className="card"><p className="eyebrow">Detected meal</p><h2>{analysis.status === 'calculated' ? 'Ready to log' : analysis.status === 'requires_food_selection' ? 'Needs confirmation' : 'Nutrition reference unavailable'}</h2>{analysis.status === 'calculated' && !analysis.analysis_session_id && <p>{analysis.food?.name}</p>}<div className="metric-card-grid"><article className="metric-card"><span>Whole meal weight entered for test</span><strong className="numeric">{measuredWeight} g</strong></article><article className="metric-card"><span>Detected components</span><strong>{components.length}</strong></article></div></section><section className="card"><h2>Meal components</h2><div className="meal-items">{components.map(component => <ComponentCard key={component.component_id} component={component} selecting={selecting} onSelect={onSelect} />)}</div></section>{analysis.status === 'calculated' && <section className="card"><h2>Total nutrition</h2><NutrientTotals totals={analysis.nutrition} /><div className="inline-actions"><button disabled={saving} onClick={onSave}>{saving ? 'Logging meal…' : analysis.analysis_session_id ? 'Log meal' : 'Confirm and save meal'}</button><button className="secondary-button" disabled={saving} onClick={onReset}>Start over</button></div></section>}{analysis.status === 'nutrition_reference_not_found' && <section className="card"><p>One or more components have no validated nutrition reference. No meal total has been calculated.</p><button onClick={onReset}>Try another photo</button></section>}</div>
}
