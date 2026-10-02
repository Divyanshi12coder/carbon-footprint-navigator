import { UserPlus } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'

import { Button } from '../../components/ui/Button'
import { useAuth } from '../../hooks/useAuth'
import { errorMessage } from '../../utils/format'
import { validateEmail, validateName, validatePassword } from '../../utils/validation'
import { AuthShell } from './AuthShell'

export default function RegisterPage() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ name: '', email: '', password: '' })
  const [touched, setTouched] = useState<Record<string, boolean>>({})
  const [serverError, setServerError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const errors = {
    name: validateName(form.name),
    email: validateEmail(form.email),
    password: validatePassword(form.password),
  }
  const valid = !errors.name && !errors.email && !errors.password
  const show = (k: keyof typeof errors) => (touched[k] ? errors[k] : null)

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setTouched({ name: true, email: true, password: true })
    if (!valid) return
    setServerError(null)
    setLoading(true)
    try {
      await register(form.name.trim(), form.email.trim(), form.password)
      toast.success('Account created — let’s set your baseline.')
      navigate('/onboarding', { replace: true })
    } catch (err) {
      setServerError(errorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  const field = (key: 'name' | 'email' | 'password', label: string, type: string, autoComplete: string, hint?: string) => (
    <div>
      <label htmlFor={key} className="label">{label}</label>
      <input
        id={key}
        type={type}
        autoComplete={autoComplete}
        className="input"
        value={form[key]}
        aria-invalid={Boolean(show(key))}
        aria-describedby={`${key}-msg`}
        onChange={(e) => setForm({ ...form, [key]: e.target.value })}
        onBlur={() => setTouched({ ...touched, [key]: true })}
      />
      <p id={`${key}-msg`} className={`mt-1 text-xs ${show(key) ? 'text-red-600' : 'text-muted'}`}>{show(key) ?? hint ?? ''}</p>
    </div>
  )

  return (
    <AuthShell
      title="Create your account"
      subtitle="Measure your footprint with transparent, sourced calculations."
      footer={<>Already have an account? <Link to="/login" className="font-semibold text-brand hover:underline">Sign in</Link></>}
    >
      <form onSubmit={onSubmit} className="space-y-3" noValidate>
        {serverError && <p role="alert" className="rounded-xl border border-red-200 bg-red-50 px-3.5 py-2.5 text-sm text-red-700">{serverError}</p>}
        {field('name', 'Full name', 'text', 'name')}
        {field('email', 'Email', 'email', 'email')}
        {field('password', 'Password', 'password', 'new-password', 'At least 8 characters with a letter and a number.')}
        <Button type="submit" className="w-full" size="lg" loading={loading} icon={<UserPlus className="h-4 w-4" />}>Create account</Button>
        <p className="text-xs text-muted">Passwords are hashed with bcrypt and never stored in plain text.</p>
      </form>
    </AuthShell>
  )
}
