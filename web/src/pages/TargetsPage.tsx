import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { ApiError } from '../api/client'
import { queryKeys } from '../api/query-keys'
import { targetsApi } from '../api/targets'
import type { NutritionTargetUpdateRequest, TargetSourceType } from '../api/types'
import { StateMessage } from '../components/StateMessage'
import { humanize, nutrientLabels, type NutrientKey } from '../utils/format-nutrition'

const nutrientKeys: NutrientKey[] = ['calories', 'protein_g', 'carbohydrates_g', 'fat_g', 'fiber_g']
const sourceTypes: TargetSourceType[] = ['manual', 'researcher_assigned', 'professional_assigned']
type TargetForm = Record<NutrientKey, string> & { source_type: TargetSourceType; source_reference: string; notes: string }
const emptyTargets: TargetForm = { calories: '', protein_g: '', carbohydrates_g: '', fat_g: '', fiber_g: '', source_type: 'manual', source_reference: '', notes: '' }

export function TargetsPage() {
  const queryClient = useQueryClient()
  const targets = useQuery({ queryKey: queryKeys.targets, queryFn: targetsApi.get, retry: false })
  const [form, setForm] = useState<TargetForm>(emptyTargets)
  const [saved, setSaved] = useState(false)
  useEffect(() => { if (targets.data) setForm({ calories: targets.data.calories ?? '', protein_g: targets.data.protein_g ?? '', carbohydrates_g: targets.data.carbohydrates_g ?? '', fat_g: targets.data.fat_g ?? '', fiber_g: targets.data.fiber_g ?? '', source_type: targets.data.source_type, source_reference: targets.data.source_reference ?? '', notes: targets.data.notes ?? '' }) }, [targets.data])
  const isMissing = targets.error instanceof ApiError && targets.error.status === 404
  const save = useMutation({ mutationFn: targetsApi.replace, onSuccess: (savedTargets) => { queryClient.setQueryData(queryKeys.targets, savedTargets); queryClient.invalidateQueries({ queryKey: ['progress'] }); setSaved(true) } })
  function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); setSaved(false); const request: NutritionTargetUpdateRequest = { calories: form.calories || null, protein_g: form.protein_g || null, carbohydrates_g: form.carbohydrates_g || null, fat_g: form.fat_g || null, fiber_g: form.fiber_g || null, source_type: form.source_type, source_reference: form.source_reference || null, notes: form.notes || null }; save.mutate(request) }
  if (targets.isPending) return <StateMessage>Loading nutrition targets…</StateMessage>
  if (targets.isError && !isMissing) return <StateMessage kind="error">Unable to load nutrition targets. Please check your connection and try again.</StateMessage>
  return <div className="page-stack"><header className="page-header"><p className="eyebrow">Targets</p><h1>Configured nutrition targets</h1><p className="muted">Targets are explicitly configured; this app does not calculate them.</p></header>{isMissing && <StateMessage>No nutrition targets have been configured yet.</StateMessage>}{saved && <StateMessage kind="success">Nutrition targets saved.</StateMessage>}{save.isError && <StateMessage kind="error">{save.error instanceof ApiError ? save.error.detail : 'Unable to save nutrition targets.'}</StateMessage>}
    <form className="card form-card" onSubmit={submit}><div className="form-grid">{nutrientKeys.map((key) => <label key={key}>{nutrientLabels[key]} {key === 'calories' ? '(kcal)' : '(g)'}<input type="number" min="0.001" step="any" value={form[key]} onChange={(event) => setForm({ ...form, [key]: event.target.value })} /></label>)}<label>Source type<select value={form.source_type} onChange={(event) => setForm({ ...form, source_type: event.target.value as TargetSourceType })}>{sourceTypes.map((value) => <option key={value} value={value}>{humanize(value)}</option>)}</select></label><label>Source reference<input maxLength={255} value={form.source_reference} onChange={(event) => setForm({ ...form, source_reference: event.target.value })} /></label></div><label>Notes<textarea maxLength={500} value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} /></label><button type="submit" disabled={save.isPending}>{save.isPending ? 'Saving…' : 'Save targets'}</button></form>
  </div>
}
