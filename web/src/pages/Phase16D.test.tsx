import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, it, vi } from 'vitest'

import { ScanPage } from './ScanPage'

const totals = { calories: '250.500', protein_g: '15.000', carbohydrates_g: '20.000', fat_g: '10.000', fiber_g: '3.000' }
const component = { component_id: 'component-1', recognized_name: 'Pork sinigang', raw_estimated_proportion: '0.55', normalized_proportion: '0.55', estimated_weight_grams: '275.000', weight_source: 'ai_estimate', resolution_status: 'resolved', nutrition_source: 'ai_recipe_estimate', resolved_reference: null, candidates: [], nutrition: totals, composite_estimation: true }
const composed = { status: 'calculated' as const, analysis_session_id: 7, analysis_session_expires_at: '2026-08-26T00:00:00Z', measured_weight_grams: '500.000', nutrition: totals, recognition_source: 'gemini', recognized_foods: [{ name: 'Pork sinigang' }], components: [component] }
const legacyCalculated = { status: 'calculated' as const, food: { id: 14, name: 'Canonical Rice' }, weight_grams: '150.000', weight_source: 'manual' as const, nutrition: totals, recognition_source: 'gemini', recognized_foods: [{ name: 'Rice' }] }

function json(body: unknown, status = 200) { return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }) }
function renderScan(client = new QueryClient({ defaultOptions: { queries: { retry: false } } })) { return render(<QueryClientProvider client={client}><ScanPage /></QueryClientProvider>) }
function selectUpload(file: File) {
  const input = document.getElementById('scan-upload') as HTMLInputElement
  fireEvent.change(input, { target: { files: [file] } })
}
function image() { return new File(['image'], 'meal.jpg', { type: 'image/jpeg' }) }
async function fillValidScan() { selectUpload(image()); await userEvent.setup().type(screen.getByLabelText('Meal weight (g)'), '500') }

afterEach(() => { cleanup(); sessionStorage.clear(); vi.unstubAllGlobals() })

it('disables analysis without an image or valid test weight and exposes mobile camera capture', async () => {
  renderScan()
  const analyze = screen.getByRole('button', { name: 'Analyze meal' })
  expect(analyze).toBeDisabled()
  expect(screen.getByLabelText('Take photo')).toHaveAttribute('accept', 'image/*')
  expect(screen.getByLabelText('Take photo')).toHaveAttribute('capture', 'environment')
  selectUpload(image())
  expect(analyze).toBeDisabled()
  await userEvent.setup().type(screen.getByLabelText('Meal weight (g)'), '5001')
  expect(analyze).toBeDisabled()
})

it('shows, replaces, clears, and revokes transient object-url previews', async () => {
  const createObjectURL = vi.fn().mockReturnValueOnce('blob:first').mockReturnValueOnce('blob:second')
  const revokeObjectURL = vi.fn()
  vi.stubGlobal('URL', { createObjectURL, revokeObjectURL })
  renderScan()
  selectUpload(image())
  expect(await screen.findByAltText('Selected food preview')).toHaveAttribute('src', 'blob:first')
  selectUpload(new File(['image-2'], 'replacement.png', { type: 'image/png' }))
  expect(await screen.findByAltText('Selected food preview')).toHaveAttribute('src', 'blob:second')
  expect(revokeObjectURL).toHaveBeenCalledWith('blob:first')
  await userEvent.setup().click(screen.getByRole('button', { name: 'Clear image' }))
  expect(screen.queryByAltText('Selected food preview')).not.toBeInTheDocument()
  expect(revokeObjectURL).toHaveBeenCalledWith('blob:second')
})

it('uses authenticated multipart file and weight fields, without setting Content-Type', async () => {
  sessionStorage.setItem('nutribox.access_token', 'test-token')
  const fetchMock = vi.fn().mockResolvedValue(json(legacyCalculated))
  vi.stubGlobal('fetch', fetchMock)
  renderScan()
  await fillValidScan()
  await userEvent.setup().click(screen.getByRole('button', { name: 'Analyze meal' }))
  expect(await screen.findByText('Canonical Rice')).toBeInTheDocument()
  const [, init] = fetchMock.mock.calls[0] as [string, RequestInit]
  const form = init.body as FormData
  expect(form.get('file')).toBeInstanceOf(File)
  expect(form.get('weight_grams')).toBe('500')
  expect(new Headers(init.headers).get('Authorization')).toBe('Bearer test-token')
  expect(new Headers(init.headers).has('Content-Type')).toBe(false)
})

it('renders composed results with whole test weight, estimated portions, and composite provenance', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json(composed)))
  renderScan()
  await fillValidScan()
  await userEvent.setup().click(screen.getByRole('button', { name: 'Analyze meal' }))
  expect(await screen.findByText('Whole meal weight entered for test')).toBeInTheDocument()
  expect(screen.getByText('500.000 g')).toBeInTheDocument()
  expect(screen.getByText('Estimated component portion')).toBeInTheDocument()
  expect(screen.getByText('Nutrition source: Estimated from dish composition')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Log meal' })).toBeInTheDocument()
})

it('selects an ambiguous component by candidate_id without rerunning analysis', async () => {
  const awaitingSelection = { ...composed, status: 'requires_food_selection' as const, components: [{ ...component, resolution_status: 'requires_food_selection', nutrition_source: null, nutrition: null, composite_estimation: false, candidates: [{ candidate_id: 'candidate-b', name: 'Rice, cooked', source: 'usda', source_reference_id: '222' }] }] }
  const fetchMock = vi.fn().mockResolvedValueOnce(json(awaitingSelection)).mockResolvedValueOnce(json(composed))
  vi.stubGlobal('fetch', fetchMock)
  renderScan()
  await fillValidScan()
  await userEvent.setup().click(screen.getByRole('button', { name: 'Analyze meal' }))
  await userEvent.setup().click(await screen.findByRole('radio'))
  await userEvent.setup().click(screen.getByRole('button', { name: 'Confirm selection' }))
  expect(await screen.findByRole('button', { name: 'Log meal' })).toBeInTheDocument()
  expect(fetchMock).toHaveBeenCalledTimes(2)
  expect(fetchMock.mock.calls[1][0]).toContain('/api/meals/analysis-sessions/7/selections')
  expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toEqual({ component_id: 'component-1', candidate_id: 'candidate-b' })
})

it('shows unresolved components safely without fabricating totals', async () => {
  const unresolved = { ...composed, status: 'nutrition_reference_not_found' as const, components: [{ ...component, recognized_name: 'Dipping sauce', resolution_status: 'nutrition_reference_not_found', nutrition_source: null, nutrition: null, composite_estimation: false }] }
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json(unresolved)))
  renderScan()
  await fillValidScan()
  await userEvent.setup().click(screen.getByRole('button', { name: 'Analyze meal' }))
  expect(await screen.findByText('Dipping sauce')).toBeInTheDocument()
  expect(screen.getAllByText('Nutrition reference unavailable').length).toBeGreaterThan(0)
  expect(screen.queryByText('Total nutrition')).not.toBeInTheDocument()
})

it('logs a calculated composed meal with analysis_session_id only and clears transient scan state', async () => {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const invalidate = vi.spyOn(client, 'invalidateQueries')
  const fetchMock = vi.fn().mockResolvedValueOnce(json(composed)).mockResolvedValueOnce(json({ id: 81, totals, items: [] }, 201))
  vi.stubGlobal('fetch', fetchMock)
  renderScan(client)
  await fillValidScan()
  await userEvent.setup().click(screen.getByRole('button', { name: 'Analyze meal' }))
  await userEvent.setup().click(await screen.findByRole('button', { name: 'Log meal' }))
  expect(await screen.findByText('Meal logged successfully.')).toBeInTheDocument()
  expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toEqual({ analysis_session_id: 7 })
  expect(screen.queryByAltText('Selected food preview')).not.toBeInTheDocument()
  expect(screen.getByLabelText('Meal weight (g)')).toHaveValue(null)
  expect(invalidate).toHaveBeenCalledWith({ queryKey: ['meals'] })
  expect(invalidate).toHaveBeenCalledWith({ queryKey: ['progress'] })
})

it('retains legacy calculated-meal persistence where the backend intentionally returns no session', async () => {
  const fetchMock = vi.fn().mockResolvedValueOnce(json(legacyCalculated)).mockResolvedValueOnce(json({ id: 81, totals, items: [] }, 201))
  vi.stubGlobal('fetch', fetchMock)
  renderScan()
  await fillValidScan()
  await userEvent.setup().click(screen.getByRole('button', { name: 'Analyze meal' }))
  await userEvent.setup().click(await screen.findByRole('button', { name: 'Confirm and save meal' }))
  expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toEqual({ items: [{ food_id: 14, weight_grams: '150.000' }] })
})
