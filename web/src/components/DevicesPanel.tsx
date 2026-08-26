import { useState } from 'react'
import type { ClipboardEvent, FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { ApiError } from '../api/client'
import { devicesApi } from '../api/devices'
import type { PairedDeviceResponse } from '../api/types'
import { queryKeys } from '../api/query-keys'
import { formatLocalDateTime } from '../utils/date-time'
import { StateMessage } from './StateMessage'

const INVALID_CODE_MESSAGE = 'Pairing code is invalid or expired.'
const PAIRING_UNAVAILABLE_MESSAGE = 'Device pairing is not configured.'

function digitsOnly(value: string): string {
  return value.replace(/\D/g, '').slice(0, 6)
}

function pairingErrorMessage(error: unknown): string {
  if (error instanceof ApiError && error.status === 422) return INVALID_CODE_MESSAGE
  if (error instanceof ApiError && error.status === 503) return PAIRING_UNAVAILABLE_MESSAGE
  if (error instanceof ApiError && error.status === 401) return 'Your sign-in session has expired.'
  return 'Unable to pair the device. Please try again.'
}

function revokeErrorMessage(error: unknown): string {
  if (error instanceof ApiError && error.status === 404) return 'This device is no longer available.'
  if (error instanceof ApiError && error.status === 401) return 'Your sign-in session has expired.'
  return 'Unable to revoke the device. Please try again.'
}

export function DevicesPanel() {
  const queryClient = useQueryClient()
  const devices = useQuery({ queryKey: queryKeys.devices, queryFn: devicesApi.list, retry: false })
  const [code, setCode] = useState('')
  const [success, setSuccess] = useState<string | null>(null)
  const [deviceToRevoke, setDeviceToRevoke] = useState<PairedDeviceResponse | null>(null)

  const pair = useMutation({
    mutationFn: (pairingCode: string) => devicesApi.pair(pairingCode),
    onSuccess: () => {
      setCode('')
      setSuccess('Device paired successfully.')
      void queryClient.invalidateQueries({ queryKey: queryKeys.devices })
    },
  })
  const revoke = useMutation({
    mutationFn: devicesApi.remove,
    onSuccess: () => {
      setDeviceToRevoke(null)
      void queryClient.invalidateQueries({ queryKey: queryKeys.devices })
    },
  })

  const connectedDevices = devices.data?.devices ?? []
  const canSubmit = code.length === 6 && !pair.isPending

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!canSubmit) return
    setSuccess(null)
    pair.mutate(code)
  }

  function pasteCode(event: ClipboardEvent<HTMLInputElement>) {
    event.preventDefault()
    setCode(digitsOnly(event.clipboardData.getData('text')))
  }

  return (
    <section className="card devices-panel">
      <div className="section-heading">
        <div>
          <h2>Paired devices</h2>
          <p>Enter the six-digit code shown on your NutriBox Pi. The device keeps its own credential.</p>
        </div>
      </div>

      <form className="pair-form" onSubmit={submit}>
        <label htmlFor="device-pairing-code">
          Six-digit pairing code
          <input
            id="device-pairing-code"
            inputMode="numeric"
            autoComplete="one-time-code"
            pattern="[0-9]{6}"
            minLength={6}
            maxLength={6}
            required
            value={code}
            onChange={(event) => setCode(digitsOnly(event.target.value))}
            onPaste={pasteCode}
            placeholder="123456"
            aria-describedby="device-pairing-help"
          />
        </label>
        <p id="device-pairing-help" className="muted">The code is used only for this pairing request and is not saved in your browser.</p>
        <button type="submit" disabled={!canSubmit}>{pair.isPending ? 'Pairing device…' : 'Pair device'}</button>
      </form>

      {success && <StateMessage kind="success">{success}</StateMessage>}
      {pair.isError && <StateMessage kind="error">{pairingErrorMessage(pair.error)}</StateMessage>}

      <div className="devices-list-section">
        <h3>Your devices</h3>
        {devices.isPending ? <StateMessage>Loading paired devices…</StateMessage> : null}
        {devices.isError ? <StateMessage kind="error">Unable to load paired devices. Please try again.</StateMessage> : null}
        {!devices.isPending && !devices.isError && connectedDevices.length === 0 ? <StateMessage>No paired devices yet.</StateMessage> : null}
        {!devices.isPending && !devices.isError && connectedDevices.length > 0 ? (
          <div className="schedule-list">
            {connectedDevices.map((device) => (
              <article className="schedule-card device-card" key={device.id}>
                <div>
                  <p className="eyebrow">Paired</p>
                  <h3>{device.name}</h3>
                  <p>{device.device_type}</p>
                  <p className="muted">Paired {formatLocalDateTime(device.paired_at)}</p>
                  <p className="muted">Last seen: {device.last_seen_at ? formatLocalDateTime(device.last_seen_at) : 'Never reported'}</p>
                </div>
                <button type="button" className="secondary-button" disabled={revoke.isPending} onClick={() => setDeviceToRevoke(device)}>Revoke</button>
              </article>
            ))}
          </div>
        ) : null}
      </div>

      {revoke.isError && <StateMessage kind="error">{revokeErrorMessage(revoke.error)}</StateMessage>}
      {deviceToRevoke ? (
        <div className="confirmation-backdrop" role="presentation">
          <section className="confirmation-dialog" role="alertdialog" aria-modal="true" aria-labelledby="revoke-device-title">
            <h3 id="revoke-device-title">Revoke {deviceToRevoke.name}?</h3>
            <p>This device will no longer be authorized. You can pair it again with a new code.</p>
            <div className="inline-actions">
              <button type="button" className="secondary-button" disabled={revoke.isPending} onClick={() => setDeviceToRevoke(null)}>Cancel</button>
              <button type="button" disabled={revoke.isPending} onClick={() => revoke.mutate(deviceToRevoke.id)}>{revoke.isPending ? 'Revoking…' : 'Revoke device'}</button>
            </div>
          </section>
        </div>
      ) : null}
    </section>
  )
}
