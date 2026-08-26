import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, it, vi } from 'vitest'

import { ApiError } from '../api/client'
import { devicesApi } from '../api/devices'
import { DevicesPanel } from './DevicesPanel'

vi.mock('../api/devices', () => ({
  devicesApi: {
    list: vi.fn(),
    pair: vi.fn(),
    remove: vi.fn(),
  },
}))

const device = {
  id: 42,
  name: 'Kitchen Pi',
  device_type: 'nutribox_pi',
  paired_at: '2026-08-26T00:00:00Z',
  last_seen_at: null,
}

const mockedDevicesApi = vi.mocked(devicesApi)

function renderPanel() {
  return render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <DevicesPanel />
    </QueryClientProvider>,
  )
}

afterEach(() => {
  cleanup()
  mockedDevicesApi.list.mockReset()
  mockedDevicesApi.pair.mockReset()
  mockedDevicesApi.remove.mockReset()
  sessionStorage.clear()
  localStorage.clear()
})

it('shows loading, empty, and null last-seen device states', async () => {
  let resolveList: ((value: { devices: Array<typeof device> }) => void) | undefined
  mockedDevicesApi.list.mockReturnValue(new Promise((resolve) => { resolveList = resolve }))
  renderPanel()
  expect(screen.getByText('Loading paired devices…')).toBeInTheDocument()

  resolveList?.({ devices: [] })
  expect(await screen.findByText('No paired devices yet.')).toBeInTheDocument()

  cleanup()
  mockedDevicesApi.list.mockResolvedValue({ devices: [device] })
  renderPanel()
  expect(await screen.findByText('Kitchen Pi')).toBeInTheDocument()
  expect(screen.getByText('Last seen: Never reported')).toBeInTheDocument()
})

it('shows a safe device-list failure state', async () => {
  mockedDevicesApi.list.mockRejectedValue(new ApiError(503, 'database connection string'))
  renderPanel()

  expect(await screen.findByText('Unable to load paired devices. Please try again.')).toBeInTheDocument()
  expect(screen.queryByText('database connection string')).not.toBeInTheDocument()
})

it('accepts only six digits, supports paste, submits once, and clears the code after success', async () => {
  mockedDevicesApi.list.mockResolvedValue({ devices: [] })
  let resolvePair: ((value: typeof device) => void) | undefined
  mockedDevicesApi.pair.mockReturnValue(new Promise((resolve) => { resolvePair = resolve }))
  const user = userEvent.setup()
  renderPanel()
  const input = await screen.findByLabelText('Six-digit pairing code')

  await user.type(input, 'a12b34')
  expect(input).toHaveValue('1234')
  expect(screen.getByRole('button', { name: 'Pair device' })).toBeDisabled()

  fireEvent.paste(input, { clipboardData: { getData: () => '56 78-90' } })
  expect(input).toHaveValue('567890')
  await user.click(screen.getByRole('button', { name: 'Pair device' }))
  expect(screen.getByRole('button', { name: 'Pairing device…' })).toBeDisabled()
  expect(mockedDevicesApi.pair).toHaveBeenCalledTimes(1)
  expect(mockedDevicesApi.pair).toHaveBeenCalledWith('567890')

  resolvePair?.(device)
  expect(await screen.findByText('Device paired successfully.')).toBeInTheDocument()
  expect(input).toHaveValue('')
  expect(sessionStorage.length).toBe(0)
  expect(localStorage.length).toBe(0)
})

it.each([
  [422, 'Pairing code is invalid or expired.'],
  [503, 'Device pairing is not configured.'],
  [401, 'Your sign-in session has expired.'],
])('shows a safe pairing error for HTTP %i', async (status, message) => {
  mockedDevicesApi.list.mockResolvedValue({ devices: [] })
  mockedDevicesApi.pair.mockRejectedValue(new ApiError(status, 'raw internal backend detail'))
  const user = userEvent.setup()
  renderPanel()
  const input = await screen.findByLabelText('Six-digit pairing code')
  await user.type(input, '123456')
  await user.click(screen.getByRole('button', { name: 'Pair device' }))

  expect(await screen.findByText(message)).toBeInTheDocument()
  expect(screen.queryByText('raw internal backend detail')).not.toBeInTheDocument()
})

it('requires confirmation and revokes by the returned device id', async () => {
  mockedDevicesApi.list.mockResolvedValue({ devices: [device] })
  mockedDevicesApi.remove.mockResolvedValue(undefined)
  const user = userEvent.setup()
  renderPanel()
  await screen.findByText('Kitchen Pi')

  await user.click(screen.getByRole('button', { name: 'Revoke' }))
  expect(screen.getByRole('alertdialog', { name: 'Revoke Kitchen Pi?' })).toBeInTheDocument()
  expect(mockedDevicesApi.remove).not.toHaveBeenCalled()
  await user.click(screen.getByRole('button', { name: 'Revoke device' }))
  await waitFor(() => expect(mockedDevicesApi.remove).toHaveBeenCalled())
  expect(mockedDevicesApi.remove.mock.calls[0]?.[0]).toBe(42)
})

it('handles a missing device during revocation without exposing backend detail', async () => {
  mockedDevicesApi.list.mockResolvedValue({ devices: [device] })
  mockedDevicesApi.remove.mockRejectedValue(new ApiError(404, 'device id belongs to someone else'))
  const user = userEvent.setup()
  renderPanel()
  await screen.findByText('Kitchen Pi')
  await user.click(screen.getByRole('button', { name: 'Revoke' }))
  await user.click(screen.getByRole('button', { name: 'Revoke device' }))

  expect(await screen.findByText('This device is no longer available.')).toBeInTheDocument()
  expect(screen.queryByText('device id belongs to someone else')).not.toBeInTheDocument()
})
