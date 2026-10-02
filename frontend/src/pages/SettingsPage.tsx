import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { KeyRound, LogOut, Save, ShieldCheck } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'

import { authApi, profileApi } from '../api/endpoints'
import { Panel } from '../components/dashboard/cards'
import { Button, ButtonLink } from '../components/ui/Button'
import { CardSkeleton } from '../components/ui/feedback'
import { PageHeader } from '../components/ui/misc'
import { useAuth } from '../hooks/useAuth'
import type { Preferences } from '../types/api'
import { errorMessage } from '../utils/format'
import { validatePassword } from '../utils/validation'

function PreferencesForm({ initial }: { initial: Preferences }) {
  const qc = useQueryClient()
  const [form, setForm] = useState<Preferences>(initial)
  const savePrefs = useMutation({
    mutationFn: (p: Preferences) => profileApi.updatePreferences(p),
    onSuccess: (p) => { qc.setQueryData(['preferences'], p); toast.success('Preferences saved') },
    onError: (e) => toast.error(errorMessage(e)),
  })
  return (
            <form className="space-y-4" onSubmit={(e: FormEvent) => { e.preventDefault(); savePrefs.mutate(form) }}>
              <div>
                <label htmlFor="range" className="label">Default dashboard range</label>
                <select id="range" className="input" value={form.default_range} onChange={(e) => setForm({ ...form, default_range: e.target.value as Preferences['default_range'] })}>
                  <option value="7d">7 days</option><option value="30d">30 days</option><option value="90d">3 months</option><option value="180d">6 months</option><option value="365d">1 year</option>
                </select>
              </div>
              <div>
                <label htmlFor="unit" className="label">Preferred distance unit</label>
                <select id="unit" className="input" value={form.distance_unit} onChange={(e) => setForm({ ...form, distance_unit: e.target.value as Preferences['distance_unit'] })}>
                  <option value="km">Kilometres</option><option value="mi">Miles</option>
                </select>
                <p className="mt-1 text-xs text-muted">Distances can be entered in either unit; they are converted to km for calculation.</p>
              </div>
              <Button type="submit" loading={savePrefs.isPending} icon={<Save className="h-4 w-4" />}>Save preferences</Button>
            </form>
  )
}

export default function SettingsPage() {
  const { user, logout, acceptToken } = useAuth()
  const navigate = useNavigate()
  const prefs = useQuery({ queryKey: ['preferences'], queryFn: profileApi.preferences })

  const [pw, setPw] = useState({ current: '', next: '' })
  const pwError = pw.next ? validatePassword(pw.next) : null
  const changePw = useMutation({
    mutationFn: () => authApi.changePassword({ current_password: pw.current, new_password: pw.next }),
    onSuccess: (res) => { acceptToken(res); setPw({ current: '', next: '' }); toast.success('Password changed — other sessions were signed out') },
    onError: (e) => toast.error(errorMessage(e)),
  })

  return (
    <div>
      <PageHeader eyebrow="Settings" title="Settings" />
      <div className="grid gap-6 lg:grid-cols-2">
        <Panel title="Preferences">
          {!prefs.data ? <CardSkeleton rows={3} /> : <PreferencesForm initial={prefs.data} />}
        </Panel>

        <Panel title="Change password" subtitle="Changing your password signs out all other sessions.">
          <form className="space-y-4" onSubmit={(e: FormEvent) => { e.preventDefault(); if (!pwError && pw.current) changePw.mutate() }}>
            <div><label htmlFor="cur" className="label">Current password</label><input id="cur" type="password" autoComplete="current-password" className="input" value={pw.current} onChange={(e) => setPw({ ...pw, current: e.target.value })} /></div>
            <div>
              <label htmlFor="new" className="label">New password</label>
              <input id="new" type="password" autoComplete="new-password" className="input" aria-invalid={Boolean(pwError)} value={pw.next} onChange={(e) => setPw({ ...pw, next: e.target.value })} />
              {pwError && <p className="mt-1 text-xs text-red-600">{pwError}</p>}
            </div>
            <Button type="submit" loading={changePw.isPending} disabled={!pw.current || !pw.next || Boolean(pwError)} icon={<KeyRound className="h-4 w-4" />}>Update password</Button>
          </form>
        </Panel>

        {user?.role === 'admin' && (
          <Panel title="Administration" subtitle="Visible to administrators only">
            <ButtonLink to="/app/admin/factors" variant="secondary" icon={<ShieldCheck className="h-4 w-4" />}>Manage emission factors</ButtonLink>
          </Panel>
        )}

        <Panel title="Session">
          <p className="mb-4 text-sm text-muted">Signing out revokes every token issued to your account.</p>
          <Button variant="danger" onClick={async () => { await logout(); navigate('/login', { replace: true }) }} icon={<LogOut className="h-4 w-4" />}>Sign out everywhere</Button>
        </Panel>
      </div>
    </div>
  )
}
