import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { tokenStore } from '../api/client'
import { ActivityForm } from '../components/activities/ActivityForm'
import RegisterPage from '../pages/auth/RegisterPage'
import type { ActivityTypeSpec } from '../types/api'
import { mockFetch, renderWithProviders } from './utils'

afterEach(() => {
  vi.unstubAllGlobals()
  tokenStore.clear()
})

describe('RegisterPage', () => {
  it('blocks submission and shows field errors for invalid input', async () => {
    const fetchMock = mockFetch({})
    renderWithProviders(<RegisterPage />, { route: '/register' })
    const user = userEvent.setup()
    await user.type(screen.getByLabelText('Email'), 'not-an-email')
    await user.type(screen.getByLabelText('Password'), 'password')
    await user.click(screen.getByRole('button', { name: /create account/i }))
    expect(screen.getByText('Name is required.')).toBeInTheDocument()
    expect(screen.getByText('Enter a valid email address.')).toBeInTheDocument()
    expect(screen.getByText('Include at least one letter and one number.')).toBeInTheDocument()
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('shows the server error when the email is taken', async () => {
    mockFetch({ 'POST /auth/register': () => new Response(JSON.stringify({ detail: 'An account with this email already exists.' }), { status: 409 }) })
    renderWithProviders(<RegisterPage />, { route: '/register' })
    const user = userEvent.setup()
    await user.type(screen.getByLabelText('Full name'), 'Ada Lovelace')
    await user.type(screen.getByLabelText('Email'), 'ada@example.com')
    await user.type(screen.getByLabelText('Password'), 'Analytical1')
    await user.click(screen.getByRole('button', { name: /create account/i }))
    expect(await screen.findByRole('alert')).toHaveTextContent('already exists')
  })
})

const CAR: ActivityTypeSpec = {
  key: 'car', category: 'transport', label: 'Car journey', description: 'Driving.', quantity_label: 'Distance', units: ['km', 'mi'], mode: 'standard',
  fields: [{ name: 'fuel_type', label: 'Fuel type', type: 'select', required: true, default: 'petrol', choices: [{ value: 'petrol', label: 'Petrol' }, { value: 'electric', label: 'Electric' }], min: null, max: null, help: null }],
}

describe('ActivityForm', () => {
  it('shows a live backend estimate and submits the activity', async () => {
    const created = vi.fn()
    const fetchMock = mockFetch({
      'GET /activities/types': () => [CAR],
      'GET /activities/airports': () => [],
      'GET /profile/preferences': () => ({ distance_unit: 'km', default_range: '30d', monthly_budget_kg: null }),
      'POST /activities/preview': (_u, init) => {
        const body = JSON.parse(String(init!.body))
        return { category: 'transport', co2e_kg: body.quantity * 0.1645, factor_key: 'transport.car.petrol', factor_value: 0.1645, factor_unit: 'km',
          factor_source: 'DESNZ', factor_region: 'GLOBAL', normalized_quantity: body.quantity, calculation_method: `${body.quantity} km x 0.1645 kg CO2e/km`,
          data_quality: 'medium', assumptions: [], details: body.details }
      },
      'POST /activities': (_u, init) => {
        const body = JSON.parse(String(init!.body))
        created(body)
        return { id: 'a1', ...body, category: 'transport', details: body.details, source: 'manual', organization_id: null, created_at: '', description: null,
          emission: { id: 'e1', co2e_kg: 6.58, factor_key: 'transport.car.petrol', factor_value: 0.1645, factor_unit: 'km', factor_source: 'DESNZ',
            emission_factor_id: 'f1', normalized_quantity: 40, calculation_method: '', data_quality: 'medium', assumptions: [] } }
      },
    })
    const onSaved = vi.fn()
    renderWithProviders(<ActivityForm onSaved={onSaved} />)
    const user = userEvent.setup()
    const qty = await screen.findByLabelText('Distance')
    await user.type(qty, '40')
    expect(await screen.findByText('40 km x 0.1645 kg CO2e/km')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /save activity/i }))
    await waitFor(() => expect(onSaved).toHaveBeenCalled())
    expect(created).toHaveBeenCalledWith(expect.objectContaining({ activity_type: 'car', quantity: 40, unit: 'km', details: { fuel_type: 'petrol' } }))
    expect(fetchMock.mock.calls.some(([, init]) => (init as RequestInit | undefined)?.method === 'POST')).toBe(true)
  })

  it('disables saving for negative quantities', async () => {
    mockFetch({
      'GET /activities/types': () => [CAR],
      'GET /activities/airports': () => [],
      'GET /profile/preferences': () => ({ distance_unit: 'mi', default_range: '30d', monthly_budget_kg: null }),
      'POST /activities/preview': () => new Response(JSON.stringify({ detail: 'invalid' }), { status: 422 }),
    })
    renderWithProviders(<ActivityForm onSaved={vi.fn()} />)
    const user = userEvent.setup()
    await user.type(await screen.findByLabelText('Distance'), '-3')
    expect(screen.getByRole('button', { name: /save activity/i })).toBeDisabled()
    // Distance unit preference is applied.
    await waitFor(() => expect(screen.getByLabelText('Unit')).toHaveValue('mi'))
  })
})
