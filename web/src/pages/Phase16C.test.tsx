import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, expect, it, vi } from 'vitest'

import { decimalStringToDisplayNumber } from '../utils/chart'
import { mondayForDate } from '../utils/date-time'
import { MealDetailPage } from './MealDetailPage'
import { MealsPage } from './MealsPage'
import { ProgressPage } from './ProgressPage'

const totals = { calories: '1532.500', protein_g: '45.000', carbohydrates_g: '120.000', fat_g: '40.000', fiber_g: '12.000' }
const meal = { id: 7, recorded_at: '2026-08-11T12:00:00Z', totals, items: [{ id: 8, food: { id: 3, name: 'Stored Food Snapshot' }, weight_grams: '150.000', nutrition: totals }] }
const daily = { date: '2026-08-11', meal_count: 1, totals }
const targetStatus = { date: '2026-08-11', meal_count: 1, consumed: totals, targets: { calories: '1200.000', protein_g: null, carbohydrates_g: null, fat_g: null, fiber_g: null }, remaining: { calories: '-332.500', protein_g: null, carbohydrates_g: null, fat_g: null, fiber_g: null }, percent_of_target: { calories: '127.708', protein_g: null, carbohydrates_g: null, fat_g: null, fiber_g: null } }
const weekly = { week_start: '2026-08-10', week_end: '2026-08-16', meal_count: 1, totals, daily: [{ ...daily, date: '2026-08-10' }, { ...daily, date: '2026-08-11', meal_count: 0, totals: { ...totals, calories: '0.000' } }, { ...daily, date: '2026-08-12' }, { ...daily, date: '2026-08-13' }, { ...daily, date: '2026-08-14' }, { ...daily, date: '2026-08-15' }, { ...daily, date: '2026-08-16' }] }

function json(body: unknown, status = 200) { return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }) }
function renderPage(page: React.ReactNode, path = '/') { return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter initialEntries={[path]}>{page}</MemoryRouter></QueryClientProvider>) }
afterEach(() => { cleanup(); vi.unstubAllGlobals() })

it('lists backend meal snapshots and paginates with limit and offset', async () => {
  const fullPage = Array.from({ length: 10 }, (_, index) => ({ ...meal, id: index + 1 }))
  const fetchMock = vi.fn()
    .mockResolvedValueOnce(json({ meals: fullPage, limit: 10, offset: 0 }))
    .mockResolvedValueOnce(json({ meals: [meal], limit: 10, offset: 10 }))
  vi.stubGlobal('fetch', fetchMock)
  renderPage(<MealsPage />)
  expect((await screen.findAllByText('1 item')).length).toBe(10)
  expect(screen.getAllByText(/1532\.5 kcal/).length).toBe(10)
  expect(fetchMock.mock.calls[0][0]).toContain('limit=10&offset=0')
  await userEvent.setup().click(screen.getByRole('button', { name: 'Next' }))
  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
  expect(fetchMock.mock.calls[1][0]).toContain('limit=10&offset=10')
})

it('shows the empty recorded-data state for no meals', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json({ meals: [], limit: 10, offset: 0 })))
  renderPage(<MealsPage />)
  expect(await screen.findByText('No meals have been recorded yet.')).toBeInTheDocument()
})

it('renders stored meal-item snapshots and handles neutral meal not found', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json(meal)))
  renderPage(<Routes><Route path="/app/meals/:mealId" element={<MealDetailPage />} /></Routes>, '/app/meals/7')
  expect(await screen.findByText('Stored Food Snapshot')).toBeInTheDocument()
  expect(screen.getByText('150.000 g portion')).toBeInTheDocument()
  cleanup()
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json({ detail: 'Meal was not found.' }, 404)))
  renderPage(<Routes><Route path="/app/meals/:mealId" element={<MealDetailPage />} /></Routes>, '/app/meals/999')
  expect(await screen.findByText('Meal not found.')).toBeInTheDocument()
})

it('uses backend progress endpoints with date, timezone, Monday weeks, summary averages, and targets', async () => {
  const fetchMock = vi.fn((input: string) => {
    if (input.includes('/weekly')) return Promise.resolve(json(weekly))
    if (input.includes('/summary')) return Promise.resolve(json({ period_start: '2026-07-13', period_end: '2026-08-11', meal_count: 3, days_with_meals: 2, totals, daily_average: { ...totals, calories: '51.083' }, daily: weekly.daily }))
    if (input.includes('/target-status')) return Promise.resolve(json(targetStatus))
    return Promise.resolve(json(daily))
  })
  vi.stubGlobal('fetch', fetchMock)
  renderPage(<ProgressPage />)
  expect(await screen.findByText('127.708%')).toBeInTheDocument()
  expect(screen.getByText('Above configured target by 332.5 kcal')).toBeInTheDocument()
  expect(screen.getByText('51.083 kcal')).toBeInTheDocument()
  fireEvent.change(screen.getByLabelText('Date'), { target: { value: '2026-08-12' } })
  await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => String(url).includes('date=2026-08-12'))).toBe(true))
  expect(mondayForDate('2026-08-12')).toBe('2026-08-10')
  expect(fetchMock.mock.calls.some(([url]) => String(url).includes('week_start=2026-08-10'))).toBe(true)
})

it('converts Decimal strings only for chart display and rejects invalid numeric values', () => {
  const source = '1532.500'
  expect(decimalStringToDisplayNumber(source)).toBe(1532.5)
  expect(source).toBe('1532.500')
  expect(decimalStringToDisplayNumber('not-a-number')).toBeNull()
  expect(decimalStringToDisplayNumber('Infinity')).toBeNull()
})
