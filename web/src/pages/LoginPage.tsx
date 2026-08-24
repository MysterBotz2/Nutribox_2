import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'

import { ApiError } from '../api/client'
import { useAuth } from '../auth/useAuth'

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string>()
  const [isSubmitting, setIsSubmitting] = useState(false)
  useEffect(() => { document.title = 'NutriBox' }, [])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(undefined)
    setIsSubmitting(true)
    try {
      await login(email, password)
      navigate('/app', { replace: true })
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.detail : 'Unable to sign in.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <main className="auth-page auth-split-page">
      <section className="auth-hero" aria-label="NutriBox nutrition companion">
        <div className="auth-hero-orb auth-hero-orb-one" />
        <div className="auth-hero-orb auth-hero-orb-two" />
        <div className="auth-hero-content">
          <div className="auth-brand"><span className="brand-mark">N</span><strong>NutriBox</strong></div>
          <p className="eyebrow">Your nutrition companion</p>
          <h2>Make every meal count.</h2>
          <p>Recognize meals, understand nutrition, and build healthier routines—one practical choice at a time.</p>
          <div className="auth-visual" aria-hidden="true">
            <div className="auth-bowl"><i /><i /><i /><b /></div>
            <div className="auth-metric auth-metric-calories"><span>Today</span><strong>1,240</strong><small>kcal logged</small></div>
            <div className="auth-metric auth-metric-protein"><span>Protein</span><strong>62g</strong><em /></div>
          </div>
        </div>
      </section>
      <section className="auth-panel">
      <section className="auth-card" aria-labelledby="login-title">
        <p className="eyebrow">NutriBox account</p>
        <h1 id="login-title">Welcome back to NutriBox</h1>
        <h2 className="sr-only">Sign in</h2>
        <p className="auth-subtitle">Sign in to continue tracking the meals and moments that matter.</p>
        {location.state?.registered && <p className="success" role="status">Registration complete. You can sign in now.</p>}
        {error && <p className="error" role="alert">{error}</p>}
        <form onSubmit={submit}>
          <label htmlFor="login-email">Email</label>
          <input id="login-email" type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
          <label htmlFor="login-password">Password</label>
          <input id="login-password" type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required />
          <button type="submit" disabled={isSubmitting}>{isSubmitting ? 'Signing in…' : 'Sign in'}</button>
        </form>
        <p className="auth-register">New to NutriBox? <Link to="/register">Create an account</Link>.</p>
      </section>
      </section>
    </main>
  )
}
