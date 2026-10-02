import { LogIn } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'

import { Button } from '../../components/ui/Button'
import { useAuth } from '../../hooks/useAuth'
import { errorMessage } from '../../utils/format'
import { AuthShell } from './AuthShell'

const DEMO = { email: 'demo@carbonnavigator.app', password: 'DemoPass123!' }

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const state = (location.state ?? {}) as { from?: string; demo?: boolean }
  const [email, setEmail] = useState(state.demo ? DEMO.email : '')
  const [password, setPassword] = useState(state.demo ? DEMO.password : '')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const user = await login(email.trim(), password)
      toast.success(`Welcome back, ${user.full_name.split(' ')[0]}`)
      navigate(user.onboarding_completed ? state.from ?? '/app' : '/onboarding', { replace: true })
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthShell
      title="Sign in"
      subtitle="Pick up where you left off."
      footer={<>New here? <Link to="/register" className="font-semibold text-brand hover:underline">Create an account</Link></>}
    >
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        {error && <p role="alert" className="rounded-xl border border-red-200 bg-red-50 px-3.5 py-2.5 text-sm text-red-700">{error}</p>}
        <div>
          <label htmlFor="email" className="label">Email</label>
          <input id="email" type="email" autoComplete="email" required className="input" value={email} onChange={(e) => setEmail(e.target.value)} />
        </div>
        <div>
          <label htmlFor="password" className="label">Password</label>
          <input id="password" type="password" autoComplete="current-password" required className="input" value={password} onChange={(e) => setPassword(e.target.value)} />
        </div>
        <Button type="submit" className="w-full" size="lg" loading={loading} disabled={!email || !password} icon={<LogIn className="h-4 w-4" />}>
          Sign in
        </Button>
        <button type="button" className="w-full text-center text-sm font-medium text-brand hover:underline"
          onClick={() => { setEmail(DEMO.email); setPassword(DEMO.password) }}>
          Use the demo account
        </button>
        <p className="text-center text-xs text-muted">The demo account exists when the server is started with seeded demo data.</p>
      </form>
    </AuthShell>
  )
}
