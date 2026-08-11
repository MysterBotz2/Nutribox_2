import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { ApiError } from '../api/client'
import { useAuth } from '../auth/useAuth'

export function RegisterPage() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [error, setError] = useState<string>()
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    setError(undefined)
    setIsSubmitting(true)
    try {
      await register({
        email: String(form.get('email')),
        password: String(form.get('password')),
        first_name: String(form.get('firstName')),
        last_name: String(form.get('lastName')),
      })
      navigate('/login', { replace: true, state: { registered: true } })
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.detail : 'Unable to register.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card" aria-labelledby="register-title">
        <p className="eyebrow">Nutri-Box</p>
        <h1 id="register-title">Create an account</h1>
        {error && <p className="error" role="alert">{error}</p>}
        <form onSubmit={submit}>
          <label htmlFor="register-first-name">First name</label>
          <input id="register-first-name" name="firstName" autoComplete="given-name" required maxLength={80} />
          <label htmlFor="register-last-name">Last name</label>
          <input id="register-last-name" name="lastName" autoComplete="family-name" required maxLength={80} />
          <label htmlFor="register-email">Email</label>
          <input id="register-email" name="email" type="email" autoComplete="email" required />
          <label htmlFor="register-password">Password</label>
          <input id="register-password" name="password" type="password" autoComplete="new-password" minLength={12} maxLength={128} required />
          <button type="submit" disabled={isSubmitting}>{isSubmitting ? 'Creating account…' : 'Create account'}</button>
        </form>
        <p>Already registered? <Link to="/login">Sign in</Link>.</p>
      </section>
    </main>
  )
}
