import { AlertTriangle, RotateCcw } from 'lucide-react'
import { Component, type ErrorInfo, type ReactNode } from 'react'

interface State {
  error: Error | null
}

/** Catches render errors so a failing page shows a recovery screen instead of a blank app. */
export class ErrorBoundary extends Component<{ children: ReactNode; resetKey?: string }, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('UI error', error, info.componentStack)
  }

  componentDidUpdate(prev: { resetKey?: string }) {
    if (prev.resetKey !== this.props.resetKey && this.state.error) this.setState({ error: null })
  }

  render() {
    if (!this.state.error) return this.props.children
    return (
      <div role="alert" className="card mx-auto my-10 max-w-lg p-8 text-center">
        <AlertTriangle className="mx-auto h-10 w-10 text-amber-600" aria-hidden />
        <h1 className="mt-4 text-xl font-bold text-forest">Something went wrong on this page</h1>
        <p className="mt-2 text-sm text-muted">The rest of the app still works. Try reloading, or head back to the dashboard.</p>
        <div className="mt-6 flex justify-center gap-2">
          <button type="button" onClick={() => window.location.reload()} className="inline-flex items-center gap-2 rounded-xl bg-brand px-4 py-2.5 text-sm font-semibold text-white hover:bg-brand-deep">
            <RotateCcw className="h-4 w-4" aria-hidden /> Reload
          </button>
          <a href="/app" className="rounded-xl border border-line px-4 py-2.5 text-sm font-semibold text-ink hover:bg-mint/50">Dashboard</a>
        </div>
      </div>
    )
  }
}
