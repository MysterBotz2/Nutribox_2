import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, expect, it, vi } from 'vitest'

import { ScanPage } from './ScanPage'

const totals = { calories: '250.500', protein_g: '15.000', carbohydrates_g: '20.000', fat_g: '10.000', fiber_g: '3.000' }
const calculated = { status: 'calculated' as const, food: { id: 14, name: 'Canonical Rice' }, weight_grams: '150.000', weight_source: 'manual' as const, nutrition: totals, recognition_source: 'gemini', recognized_foods: [{ name: 'Rice' }] }

function json(body: unknown, status = 200) { return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }) }
function renderScan(client = new QueryClient({ defaultOptions: { queries: { retry: false } } })) { return render(<QueryClientProvider client={client}><MemoryRouter initialEntries={['/app/scan']}><Routes><Route path="/app/scan" element={<ScanPage />} /><Route path="/app/meals/:mealId" element={<p>Saved meal detail</p>} /></Routes></MemoryRouter></QueryClientProvider>) }
function selectFile(file: File) { fireEvent.change(screen.getByLabelText('Food image'), { target: { files: [file] } }) }

afterEach(() => { cleanup(); vi.unstubAllGlobals() })

it.each(['image/jpeg', 'image/png', 'image/webp'])('accepts %s and creates/revokes a local preview', async (type) => {
  const createObjectURL = vi.fn(() => 'blob:preview')
  const revokeObjectURL = vi.fn()
  vi.stubGlobal('URL', { createObjectURL, revokeObjectURL })
  renderScan()
  selectFile(new File(['image'], `meal.${type.split('/')[1]}`, { type }))
  expect(await screen.findByAltText('Selected food preview')).toHaveAttribute('src', 'blob:preview')
  await userEvent.setup().click(screen.getByRole('button', { name: 'Start over' }))
  expect(revokeObjectURL).toHaveBeenCalledWith('blob:preview')
})

it('rejects unsupported files before upload', () => {
  renderScan()
  selectFile(new File(['text'], 'meal.txt', { type: 'text/plain' }))
  expect(screen.getByText('Choose a JPEG, PNG, or WEBP image.')).toBeInTheDocument()
})

it('sends exact multipart fields without manually setting Content-Type and renders calculated nutrition', async () => {
  const fetchMock = vi.fn().mockResolvedValue(json(calculated))
  vi.stubGlobal('fetch', fetchMock)
  renderScan()
  selectFile(new File(['image'], 'meal.jpg', { type: 'image/jpeg' }))
  await userEvent.setup().type(screen.getByLabelText('Portion weight (grams)'), '150')
  await userEvent.setup().click(screen.getByRole('button', { name: 'Analyze image' }))
  expect(await screen.findByText('Canonical Rice')).toBeInTheDocument()
  expect(screen.getByText('250.5 kcal')).toBeInTheDocument()
  const [, init] = fetchMock.mock.calls[0] as [string, RequestInit]
  const form = init.body as FormData
  expect(form.get('file')).toBeInstanceOf(File)
  expect(form.get('weight_grams')).toBe('150')
  expect(new Headers(init.headers).has('Content-Type')).toBe(false)
})

it.each([
  [{ status: 'food_not_recognized', recognition_source: 'simulated', recognized_foods: [] }, 'No identifiable food was recognized in this image.'],
  [{ status: 'nutrition_reference_not_found', recognition_source: 'gemini', recognized_foods: [{ name: 'Chicken Adobo' }] }, 'Chicken Adobo was recognized, but a validated nutrition reference is not currently available.'],
  [{ status: 'requires_food_selection', recognition_source: 'gemini', recognized_foods: [{ name: 'Rice' }, { name: 'Fish' }] }, 'Multiple foods were recognized. Nutri-Box did not divide the supplied plate weight between them.'],
])('renders backend domain state without inventing nutrition', async (response, message) => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json(response)))
  renderScan()
  selectFile(new File(['image'], 'meal.png', { type: 'image/png' }))
  await userEvent.setup().type(screen.getByLabelText('Portion weight (grams)'), '200')
  await userEvent.setup().click(screen.getByRole('button', { name: 'Analyze image' }))
  expect(await screen.findByText(message)).toBeInTheDocument()
})

it('saves a calculated meal with canonical id and weight only, invalidates caches, and navigates', async () => {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const invalidate = vi.spyOn(client, 'invalidateQueries')
  const fetchMock = vi.fn().mockResolvedValueOnce(json(calculated)).mockResolvedValueOnce(json({ id: 81, recorded_at: '2026-08-11T00:00:00Z', totals, items: [] }, 201))
  vi.stubGlobal('fetch', fetchMock)
  renderScan(client)
  selectFile(new File(['image'], 'meal.webp', { type: 'image/webp' }))
  await userEvent.setup().type(screen.getByLabelText('Portion weight (grams)'), '150')
  await userEvent.setup().click(screen.getByRole('button', { name: 'Analyze image' }))
  await screen.findByText('Canonical Rice')
  await userEvent.setup().click(screen.getByRole('button', { name: 'Confirm and save meal' }))
  expect(await screen.findByText('Saved meal detail')).toBeInTheDocument()
  const request = JSON.parse(fetchMock.mock.calls[1][1].body)
  expect(request).toEqual({ items: [{ food_id: 14, weight_grams: '150.000' }] })
  expect(invalidate).toHaveBeenCalledWith({ queryKey: ['meals'] })
  expect(invalidate).toHaveBeenCalledWith({ queryKey: ['progress'] })
})

it.each([429, 502, 503, 504])('shows a safe provider failure for HTTP %i', async (status) => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json({ detail: 'Food recognition provider is unavailable.' }, status)))
  renderScan()
  selectFile(new File(['image'], 'meal.jpg', { type: 'image/jpeg' }))
  await userEvent.setup().type(screen.getByLabelText('Portion weight (grams)'), '150')
  await userEvent.setup().click(screen.getByRole('button', { name: 'Analyze image' }))
  expect(await screen.findByText('Food recognition provider is unavailable.')).toBeInTheDocument()
})
