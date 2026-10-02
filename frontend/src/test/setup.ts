import '@testing-library/jest-dom/vitest'

import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

// Vitest globals are off, so Testing Library's auto-cleanup isn't registered — do it explicitly.
afterEach(() => {
  cleanup()
  localStorage.clear()
})
