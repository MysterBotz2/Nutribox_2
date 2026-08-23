import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ApiError } from '../api/client'
import { queryKeys } from '../api/query-keys'
import { scheduleApi } from '../api/schedule'
import type { ScheduledMealResponse } from '../api/types'
import { StateMessage } from '../components/StateMessage'
import { formatLocalDateTime } from '../utils/date-time'

type ScheduleForm = { title: string; scheduledFor: string; notes: string }
const emptyForm: ScheduleForm = { title: '', scheduledFor: '', notes: '' }
function toLocalInput(iso: string): string { const date = new Date(iso); return new Date(date.getTime() - date.getTimezoneOffset() * 60_000).toISOString().slice(0, 16) }

export function SchedulePage() {
  const queryClient = useQueryClient()
  const scheduledMeals = useQuery({ queryKey: queryKeys.schedule, queryFn: scheduleApi.list, retry: false })
  const [form, setForm] = useState<ScheduleForm>(emptyForm)
  const [editing, setEditing] = useState<ScheduledMealResponse | null>(null)
  const save = useMutation({ mutationFn: () => { const body = { title: form.title.trim(), scheduled_for: new Date(form.scheduledFor).toISOString(), notes: form.notes.trim() || null }; return editing ? scheduleApi.update(editing.id, body) : scheduleApi.create(body) }, onSuccess: () => { queryClient.invalidateQueries({ queryKey: queryKeys.schedule }); setForm(emptyForm); setEditing(null) } })
  const remove = useMutation({ mutationFn: scheduleApi.remove, onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.schedule }) })
  useEffect(() => { if (editing) setForm({ title: editing.title, scheduledFor: toLocalInput(editing.scheduled_for), notes: editing.notes ?? '' }) }, [editing])
  function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); save.mutate() }
  return <div className="page-stack"><header className="page-header"><p className="eyebrow">Schedule</p><h1>Planned meals</h1><p className="muted">Scheduled meals are plans, not logged nutrition.</p></header>
    <form className="card form-card" onSubmit={submit}><div className="section-heading"><div><h2>{editing ? 'Edit scheduled meal' : 'Schedule a meal'}</h2><p>{editing ? 'Update this plan without changing recorded meals.' : 'Plans remain separate from logged meal nutrition.'}</p></div>{editing && <button className="secondary-button" type="button" onClick={() => { setEditing(null); setForm(emptyForm) }}>Cancel edit</button>}</div><div className="form-grid"><label>Title<input required maxLength={160} value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} placeholder="Breakfast" /></label><label>Scheduled date and time<input required type="datetime-local" value={form.scheduledFor} onChange={(event) => setForm({ ...form, scheduledFor: event.target.value })} /></label></div><label>Notes <span className="muted">(optional)</span><textarea maxLength={1000} value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} placeholder="Example: pack lunch before leaving." /></label>{save.isError && <StateMessage kind="error">{save.error instanceof ApiError ? save.error.detail : 'Unable to save the scheduled meal.'}</StateMessage>}<button type="submit" disabled={save.isPending}>{save.isPending ? 'Saving…' : editing ? 'Save changes' : 'Schedule meal'}</button></form>
    <section className="card"><div className="section-heading"><div><h2>Upcoming schedule</h2><p>All times are shown in your local time.</p></div></div>{scheduledMeals.isPending ? <StateMessage>Loading scheduled meals…</StateMessage> : scheduledMeals.isError ? <StateMessage kind="error">Unable to load scheduled meals. Please try again.</StateMessage> : scheduledMeals.data.scheduled_meals.length === 0 ? <StateMessage>No scheduled meals yet. Create a plan when it helps your routine.</StateMessage> : <div className="schedule-list">{scheduledMeals.data.scheduled_meals.map((item) => <article className="schedule-card" key={item.id}><div><p className="eyebrow">Scheduled meal</p><h3>{item.title}</h3><p>{formatLocalDateTime(item.scheduled_for)}</p>{item.notes && <p className="muted">{item.notes}</p>}</div><div className="inline-actions"><button className="secondary-button" type="button" onClick={() => setEditing(item)}>Edit</button><button type="button" disabled={remove.isPending} onClick={() => remove.mutate(item.id)}>Delete</button></div></article>)}</div>}{remove.isError && <StateMessage kind="error">{remove.error instanceof ApiError ? remove.error.detail : 'Unable to delete the scheduled meal.'}</StateMessage>}</section></div>
}
