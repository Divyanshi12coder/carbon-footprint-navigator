import { afterEach, describe, expect, it, vi } from 'vitest'

import { api, ApiError, SESSION_EXPIRED_EVENT, tokenStore } from '../api/client'
import { offScaleCap } from '../charts/common'
import { formatKg, formatPct } from '../utils/format'
import { validateEmail, validatePassword } from '../utils/validation'
import { mockFetch } from './utils'

describe('validation (mirrors backend rules)', () => {
  it('validates email', () => {
    expect(validateEmail('')).toMatch(/required/)
    expect(validateEmail('nope')).toMatch(/valid/)
    expect(validateEmail('a@b.co')).toBeNull()
  })
  it('requires 8+ chars with a letter and a digit', () => {
    expect(validatePassword('short1')).toMatch(/8/)
    expect(validatePassword('password')).toMatch(/letter and one number/)
    expect(validatePassword('passw0rd')).toBeNull()
  })
})

describe('formatting', () => {
  it('switches to tonnes above 1000 kg', () => {
    expect(formatKg(1530)).toBe('1.53 t')
    expect(formatKg(12.345)).toBe('12.3 kg')
    expect(formatKg(null)).toBe('—')
  })
  it('signs percentages', () => {
    expect(formatPct(12.34, true)).toBe('+12.3%')
    expect(formatPct(-5, true)).toBe('−5%')
  })
})

describe('offScaleCap', () => {
  it('caps a single extreme spike but leaves normal data alone', () => {
    const normal = [5, 8, 6, 7, 9, 5, 6, 8, 7, 6]
    expect(offScaleCap(normal)).toBeNull()
    const cap = offScaleCap([...normal, 1800])
    expect(cap).not.toBeNull()
    expect(cap!).toBeLessThan(1800)
    expect(cap!).toBeGreaterThanOrEqual(9)
  })
})

describe('api client', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    tokenStore.clear()
  })

  it('sends the bearer token and parses JSON', async () => {
    tokenStore.set('abc')
    const fetchMock = mockFetch({ 'GET /auth/me': () => ({ id: '1' }) })
    await expect(api('/auth/me')).resolves.toEqual({ id: '1' })
    const headers = fetchMock.mock.calls[0][1]!.headers as Headers
    expect(headers.get('Authorization')).toBe('Bearer abc')
  })

  it('turns FastAPI validation errors into readable messages', async () => {
    mockFetch({ 'POST /activities': () => new Response(JSON.stringify({ detail: [{ loc: ['body', 'quantity'], msg: 'Input should be greater than or equal to 0' }] }), { status: 422 }) })
    await expect(api('/activities', { method: 'POST', body: '{}' })).rejects.toThrow('quantity: Input should be greater than or equal to 0')
  })

  it('clears the token and broadcasts session expiry on 401', async () => {
    tokenStore.set('expired')
    const listener = vi.fn()
    window.addEventListener(SESSION_EXPIRED_EVENT, listener)
    mockFetch({ 'GET /dashboard': () => new Response(JSON.stringify({ detail: 'Session expired. Please sign in again.' }), { status: 401 }) })
    const err = await api('/dashboard/summary').catch((e) => e)
    expect(err).toBeInstanceOf(ApiError)
    expect((err as ApiError).status).toBe(401)
    expect(tokenStore.get()).toBeNull()
    expect(listener).toHaveBeenCalledOnce()
    window.removeEventListener(SESSION_EXPIRED_EVENT, listener)
  })

  it('reports network failures', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => { throw new TypeError('Failed to fetch') }))
    await expect(api('/health')).rejects.toThrow(/Cannot reach the server/)
  })
})
