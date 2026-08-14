import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { ApiError } from '../api/client'
import { profileApi } from '../api/profile'
import { queryKeys } from '../api/query-keys'
import type { ActivityLevel, NutritionGoal, NutritionProfileUpdateRequest } from '../api/types'
import { StateMessage } from '../components/StateMessage'
import { humanize } from '../utils/format-nutrition'

const activityLevels: ActivityLevel[] = ['sedentary', 'lightly_active', 'moderately_active', 'very_active']
const nutritionGoals: NutritionGoal[] = ['maintain_weight', 'lose_weight', 'gain_weight', 'general_health']
type ProfileForm = { age: string; height_cm: string; weight_kg: string; activity_level: ActivityLevel | ''; nutrition_goal: NutritionGoal | ''; dietary_restrictions: string[]; allergies: string[] }
const emptyProfile: ProfileForm = { age: '', height_cm: '', weight_kg: '', activity_level: '', nutrition_goal: '', dietary_restrictions: [], allergies: [] }

function TagsEditor({ label, values, onChange }: { label: string; values: string[]; onChange: (values: string[]) => void }) {
  const [value, setValue] = useState('')
  function add() { const cleaned = value.trim().replace(/\s+/g, ' '); if (cleaned && !values.includes(cleaned) && values.length < 20) { onChange([...values, cleaned]); setValue('') } }
  return <fieldset className="tag-editor"><legend>{label}</legend><div className="tag-input"><input value={value} maxLength={100} onChange={(event) => setValue(event.target.value)} aria-label={`Add ${label.toLowerCase()}`} /><button type="button" className="secondary-button" onClick={add}>Add</button></div><div className="tags">{values.map((item) => <button className="tag" type="button" key={item} onClick={() => onChange(values.filter((valueItem) => valueItem !== item))}>{item} ×</button>)}</div></fieldset>
}

export function ProfilePage() {
  const queryClient = useQueryClient()
  const profile = useQuery({ queryKey: queryKeys.profile, queryFn: profileApi.get, retry: false })
  const [form, setForm] = useState<ProfileForm>(emptyProfile)
  const [saved, setSaved] = useState(false)
  useEffect(() => { if (profile.data) setForm({ age: profile.data.age?.toString() ?? '', height_cm: profile.data.height_cm ?? '', weight_kg: profile.data.weight_kg ?? '', activity_level: profile.data.activity_level ?? '', nutrition_goal: profile.data.nutrition_goal ?? '', dietary_restrictions: profile.data.dietary_restrictions ?? [], allergies: profile.data.allergies ?? [] }) }, [profile.data])
  const isMissing = profile.error instanceof ApiError && profile.error.status === 404
  const save = useMutation({ mutationFn: profileApi.replace, onSuccess: (savedProfile) => { queryClient.setQueryData(queryKeys.profile, savedProfile); setSaved(true) } })
  function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); setSaved(false); const request: NutritionProfileUpdateRequest = { age: form.age ? Number(form.age) : null, height_cm: form.height_cm || null, weight_kg: form.weight_kg || null, activity_level: form.activity_level || null, nutrition_goal: form.nutrition_goal || null, dietary_restrictions: form.dietary_restrictions, allergies: form.allergies }; save.mutate(request) }
  if (profile.isPending) return <StateMessage>Loading profile…</StateMessage>
  if (profile.isError && !isMissing) return <StateMessage kind="error">Unable to load your profile. Please check your connection and try again.</StateMessage>
  return <div className="page-stack"><header className="page-header"><p className="eyebrow">Profile</p><h1>Nutrition profile</h1><p className="muted">Profile context is separate from configured nutrition targets.</p></header>{isMissing && <StateMessage>No nutrition profile has been saved yet. Complete only the fields that apply to you.</StateMessage>}{saved && <StateMessage kind="success">Profile saved.</StateMessage>}{save.isError && <StateMessage kind="error">{save.error instanceof ApiError ? save.error.detail : 'Unable to save your profile.'}</StateMessage>}
    <form className="card form-card" onSubmit={submit}><div className="form-grid"><label>Age<input type="number" min="0" max="130" value={form.age} onChange={(event) => setForm({ ...form, age: event.target.value })} /></label><label>Height (cm)<input type="number" min="0.001" max="300" step="any" value={form.height_cm} onChange={(event) => setForm({ ...form, height_cm: event.target.value })} /></label><label>Weight (kg)<input type="number" min="0.001" max="500" step="any" value={form.weight_kg} onChange={(event) => setForm({ ...form, weight_kg: event.target.value })} /></label><label>Activity level<select value={form.activity_level} onChange={(event) => setForm({ ...form, activity_level: event.target.value as ActivityLevel | '' })}><option value="">Not specified</option>{activityLevels.map((value) => <option value={value} key={value}>{humanize(value)}</option>)}</select></label><label>Nutrition goal<select value={form.nutrition_goal} onChange={(event) => setForm({ ...form, nutrition_goal: event.target.value as NutritionGoal | '' })}><option value="">Not specified</option>{nutritionGoals.map((value) => <option value={value} key={value}>{humanize(value)}</option>)}</select></label></div><TagsEditor label="Dietary restrictions" values={form.dietary_restrictions} onChange={(dietary_restrictions) => setForm({ ...form, dietary_restrictions })} /><TagsEditor label="Allergies" values={form.allergies} onChange={(allergies) => setForm({ ...form, allergies })} /><button type="submit" disabled={save.isPending}>{save.isPending ? 'Saving…' : 'Save profile'}</button></form>
  </div>
}
