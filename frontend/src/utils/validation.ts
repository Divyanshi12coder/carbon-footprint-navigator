// Client-side checks mirror the backend's Pydantic rules so users get instant feedback;
// the backend remains the source of truth and re-validates everything.

export function validateEmail(email: string): string | null {
  if (!email.trim()) return 'Email is required.'
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) return 'Enter a valid email address.'
  return null
}

export function validatePassword(password: string): string | null {
  if (password.length < 8) return 'Use at least 8 characters.'
  if (!/[A-Za-z]/.test(password) || !/\d/.test(password)) return 'Include at least one letter and one number.'
  return null
}

export function validateName(name: string): string | null {
  return name.trim() ? null : 'Name is required.'
}
