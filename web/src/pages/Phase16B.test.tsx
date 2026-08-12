import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, expect, it, vi } from 'vitest'

import { DashboardPage } from './DashboardPage'
import { ProfilePage } from './ProfilePage'
import { TargetsPage } from './TargetsPage'

const totals = { calories: '35.500', protein_g: '4.000', carbohydrates_g: '6.000', fat_g: '1.000', fiber_g: '2.000' }

function json(body: unknown, status = 200) { return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }) }
function renderPage(page: React.ReactNode) { return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter>{page}</MemoryRouter></QueryClientProvider>) }

afterEach(() => { cleanup(); vi.unstubAllGlobals() })

it('forwards the browser timezone and renders stored dashboard totals with empty states', async () => {
  const fetchMock = vi.fn((input: string) => {
    if (input.includes('/today')) return Promise.resolve(json({ date: '2026-08-11', meal_count: 0, totals }))
    if (input.includes('/target-status')) return Promise.resolve(json({ date: '2026-08-11', meal_count: 0, consumed: totals, targets: null, remaining: null, percent_of_target: null }))
    return Promise.resolve(json({ meals: [], limit: 3, offset: 0 }))
  })
  vi.stubGlobal('fetch', fetchMock)
  renderPage(<DashboardPage />)
  expect(await screen.findByText('35.5 kcal')).toBeInTheDocument()
  expect(screen.getByText('No meals recorded for this date.')).toBeInTheDocument()
  expect(screen.getByText('No nutrition targets configured.')).toBeInTheDocument()
  expect(fetchMock.mock.calls[0][0]).toContain('timezone=')
})

it('preserves negative remaining values and percentages above one hundred', async () => {
  const fetchMock = vi.fn((input: string) => {
    if (input.includes('/today')) return Promise.resolve(json({ date: '2026-08-11', meal_count: 1, totals }))
    if (input.includes('/target-status')) return Promise.resolve(json({ date: '2026-08-11', meal_count: 1, consumed: totals, targets: { calories: '20.000', protein_g: null, carbohydrates_g: null, fat_g: null, fiber_g: null }, remaining: { calories: '-15.500', protein_g: null, carbohydrates_g: null, fat_g: null, fiber_g: null }, percent_of_target: { calories: '177.500', protein_g: null, carbohydrates_g: null, fat_g: null, fiber_g: null } }))
    return Promise.resolve(json({ meals: [], limit: 3, offset: 0 }))
  })
  vi.stubGlobal('fetch', fetchMock)
  renderPage(<DashboardPage />)
  expect(await screen.findByText('177.5%')).toBeInTheDocument()
  expect(screen.getByText('Above configured target by 15.5 kcal')).toBeInTheDocument()
})

it('treats a missing profile as setup and submits the exact profile shape', async () => {
  const fetchMock = vi.fn()
    .mockResolvedValueOnce(json({ detail: 'Nutrition profile was not found.' }, 404))
    .mockResolvedValueOnce(json({ id: 1, user_id: 1, age: 25, height_cm: '170.000', weight_kg: '65.000', activity_level: 'moderately_active', nutrition_goal: 'general_health', dietary_restrictions: ['Vegetarian'], allergies: ['Peanut'], created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z' }))
  vi.stubGlobal('fetch', fetchMock)
  renderPage(<ProfilePage />)
  expect(await screen.findByText('No nutrition profile has been saved yet. Complete only the fields that apply to you.')).toBeInTheDocument()
  const user = userEvent.setup()
  await user.type(screen.getByLabelText('Age'), '25')
  await user.selectOptions(screen.getByLabelText('Activity level'), 'moderately_active')
  await user.click(screen.getByRole('button', { name: 'Save profile' }))
  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
  const request = JSON.parse(fetchMock.mock.calls[1][1].body)
  expect(request).toMatchObject({ age: 25, activity_level: 'moderately_active', dietary_restrictions: [], allergies: [] })
})

it('supports partial targets, supported source types, and safe validation errors', async () => {
  const fetchMock = vi.fn()
    .mockResolvedValueOnce(json({ detail: 'Nutrition targets were not found.' }, 404))
    .mockResolvedValueOnce(json({ detail: [{ msg: 'At least one nutrition target value must be configured.' }] }, 422))
  vi.stubGlobal('fetch', fetchMock)
  renderPage(<TargetsPage />)
  expect(await screen.findByText('No nutrition targets have been configured yet.')).toBeInTheDocument()
  const user = userEvent.setup()
  await user.type(screen.getByLabelText('Protein (g)'), '80.5')
  await user.selectOptions(screen.getByLabelText('Source type'), 'researcher_assigned')
  await user.click(screen.getByRole('button', { name: 'Save targets' }))
  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
  const request = JSON.parse(fetchMock.mock.calls[1][1].body)
  expect(request).toMatchObject({ protein_g: '80.5', calories: null, source_type: 'researcher_assigned' })
  expect(await screen.findByText('Please correct the highlighted request fields.')).toBeInTheDocument()
})

it('loads existing profile enum values and updates bounded label arrays', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json({ id: 1, user_id: 1, age: null, height_cm: null, weight_kg: null, activity_level: 'very_active', nutrition_goal: 'general_health', dietary_restrictions: ['Vegetarian'], allergies: [], created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z' })))
  renderPage(<ProfilePage />)
  expect((await screen.findByLabelText('Activity level'))).toHaveValue('very_active')
  const user = userEvent.setup()
  await user.type(screen.getByLabelText('Add allergies'), 'Peanut')
  await user.click(screen.getAllByRole('button', { name: 'Add' })[1])
  expect(screen.getByRole('button', { name: 'Peanut ×' })).toBeInTheDocument()
})

it('refreshes progress queries after a successful target save', async () => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const invalidate = vi.spyOn(queryClient, 'invalidateQueries')
  vi.stubGlobal('fetch', vi.fn()
    .mockResolvedValueOnce(json({ detail: 'Nutrition targets were not found.' }, 404))
    .mockResolvedValueOnce(json({ id: 1, user_id: 1, calories: '2000.000', protein_g: null, carbohydrates_g: null, fat_g: null, fiber_g: null, source_type: 'manual', source_reference: null, notes: null, created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z' })))
  render(<QueryClientProvider client={queryClient}><MemoryRouter><TargetsPage /></MemoryRouter></QueryClientProvider>)
  const user = userEvent.setup()
  await screen.findByText('No nutrition targets have been configured yet.')
  await user.type(screen.getByLabelText('Calories (kcal)'), '2000')
  await user.click(screen.getByRole('button', { name: 'Save targets' }))
  await screen.findByText('Nutrition targets saved.')
  expect(invalidate).toHaveBeenCalledWith({ queryKey: ['progress'] })
})
