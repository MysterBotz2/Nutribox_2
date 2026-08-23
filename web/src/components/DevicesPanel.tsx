import { useState } from 'react'
import type { FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ApiError } from '../api/client'
import { devicesApi } from '../api/devices'
import { queryKeys } from '../api/query-keys'
import { StateMessage } from './StateMessage'
import { formatLocalDateTime } from '../utils/date-time'

export function DevicesPanel() {
  const queryClient = useQueryClient(); const devices = useQuery({ queryKey: queryKeys.devices, queryFn: devicesApi.list, retry: false }); const [code, setCode] = useState('')
  const pair = useMutation({ mutationFn: () => devicesApi.pair(code), onSuccess: () => { setCode(''); queryClient.invalidateQueries({ queryKey: queryKeys.devices }) } })
  const remove = useMutation({ mutationFn: devicesApi.remove, onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.devices }) })
  function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); pair.mutate() }
  const connectedDevices = devices.data?.devices ?? []
  return <section className="card"><h2>Devices</h2>{devices.isPending ? <StateMessage>Loading connected devices…</StateMessage> : devices.isError ? <StateMessage kind="error">Unable to load connected devices.</StateMessage> : connectedDevices.length === 0 ? <><StateMessage>No NutriBox device connected.<br />You can continue using NutriBox normally without a connected device.</StateMessage><form className="pair-form" onSubmit={submit}><label>6-digit pairing code<input inputMode="numeric" pattern="[0-9]{6}" minLength={6} maxLength={6} required value={code} onChange={(event) => setCode(event.target.value.replace(/\D/g, '').slice(0, 6))} placeholder="123456" /></label><button type="submit" disabled={pair.isPending || code.length !== 6}>{pair.isPending ? 'Connecting…' : 'Connect NutriBox'}</button></form>{pair.isError && <StateMessage kind="error">{pair.error instanceof ApiError ? pair.error.detail : 'Unable to connect the device.'}</StateMessage>}</> : <div className="schedule-list">{connectedDevices.map((device) => <article className="schedule-card" key={device.id}><div><h3>{device.name}</h3><p>{device.device_type}</p><p className="muted">Paired {formatLocalDateTime(device.paired_at)}</p></div><button type="button" disabled={remove.isPending} onClick={() => remove.mutate(device.id)}>Disconnect</button></article>)}</div>}</section>
}
