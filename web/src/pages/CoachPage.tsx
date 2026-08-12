import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { coachApi } from '../api/coach'
import { ApiError } from '../api/client'
import { profileApi } from '../api/profile'
import { queryKeys } from '../api/query-keys'
import { targetsApi } from '../api/targets'
import type { NutritionCoachResponse } from '../api/types'
import { StateMessage } from '../components/StateMessage'
import { formatLocalDateTime } from '../utils/date-time'
import { getBrowserTimezone } from '../utils/timezone'

const QUESTION_LIMIT = 500

function isMissingSetup(error: Error | null): boolean {
  return error instanceof ApiError && error.status === 404
}

function coachErrorMessage(error: Error): string {
  if (!(error instanceof ApiError)) return 'Unable to contact the Nutri-Box coach. Please try again.'
  switch (error.status) {
    case 429: return 'The coach is temporarily rate-limited. Please try again shortly.'
    case 502: return 'The coach returned an invalid response. Please try again.'
    case 503: return 'The coach is temporarily unavailable. Please try again later.'
    case 504: return 'The coach request timed out. Please try again.'
    default: return error.detail
  }
}

function SetupStatus({ name, configured, to }: { name: string; configured: boolean; to: string }) {
  return <li><strong>{name}:</strong> {configured ? 'Configured' : <><span>Not configured. </span><Link to={to}>Set up {name.toLowerCase()}</Link></>}</li>
}

export function CoachPage() {
  const timezone = getBrowserTimezone()
  const [question, setQuestion] = useState('')
  const [latestResponse, setLatestResponse] = useState<NutritionCoachResponse | null>(null)
  const [submissionError, setSubmissionError] = useState<string | null>(null)
  const profile = useQuery({ queryKey: queryKeys.profile, queryFn: profileApi.get, retry: false })
  const targets = useQuery({ queryKey: queryKeys.targets, queryFn: targetsApi.get, retry: false })
  const askCoach = useMutation({
    mutationFn: (nextQuestion: string | null) => coachApi.ask({ question: nextQuestion }, timezone),
    onSuccess: (response) => {
      setLatestResponse(response)
      setSubmissionError(null)
    },
    onError: (error) => setSubmissionError(coachErrorMessage(error)),
  })

  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (askCoach.isPending) return
    setSubmissionError(null)
    askCoach.mutate(question.trim() || null)
  }

  const profileConfigured = profile.isSuccess
  const targetsConfigured = targets.isSuccess

  return <div className="page-stack coach-page">
    <header className="page-header"><p className="eyebrow">AI Coach</p><h1>Nutrition coaching, on request</h1><p className="muted">Ask for general nutrition information using your stored Nutri-Box context.</p></header>
    <section className="card coach-context" aria-labelledby="coach-context-heading">
      <h2 id="coach-context-heading">Coach context</h2>
      <p className="muted">The backend prepares the authoritative context for each request. This preview is only for orientation.</p>
      <ul>
        <SetupStatus name="Profile" configured={profileConfigured} to="/app/profile" />
        <SetupStatus name="Nutrition targets" configured={targetsConfigured} to="/app/targets" />
        <li><strong>Today’s recorded progress:</strong> Available to the backend.</li>
      </ul>
      {(profile.isPending || targets.isPending) && <StateMessage>Checking optional profile and target setup…</StateMessage>}
      {!profile.isPending && !profileConfigured && !isMissingSetup(profile.error) && <StateMessage kind="error">Profile setup status could not be loaded. Coaching is still available.</StateMessage>}
      {!targets.isPending && !targetsConfigured && !isMissingSetup(targets.error) && <StateMessage kind="error">Target setup status could not be loaded. Coaching is still available.</StateMessage>}
    </section>
    <section className="card coach-form-card" aria-labelledby="ask-coach-heading">
      <h2 id="ask-coach-heading">Ask the coach</h2>
      <p className="muted">A question is optional. Each request is independent; previous questions are not saved as a conversation.</p>
      <form onSubmit={submit}>
        <label htmlFor="coach-question">Optional nutrition question
          <textarea id="coach-question" value={question} maxLength={QUESTION_LIMIT} onChange={(event) => setQuestion(event.target.value)} aria-describedby="coach-question-limit" placeholder="For example: What should I review in today’s recorded meals?" />
        </label>
        <p id="coach-question-limit" className="muted coach-character-count">{question.length}/{QUESTION_LIMIT} characters</p>
        <button type="submit" disabled={askCoach.isPending}>{askCoach.isPending ? 'Asking coach…' : 'Ask Coach'}</button>
      </form>
      {askCoach.isPending && <StateMessage>Preparing your coaching response…</StateMessage>}
      {submissionError && <StateMessage kind="error">{submissionError}</StateMessage>}
    </section>
    {latestResponse && <section className="card coach-response" aria-live="polite" aria-labelledby="coach-response-heading">
      <div className="section-heading"><div><h2 id="coach-response-heading">Coach response</h2><p>Generated {formatLocalDateTime(latestResponse.generated_at)}</p></div><span className="coach-provider">Provider: {latestResponse.provider}</span></div>
      <p className="coach-message">{latestResponse.message}</p>
      <h3>Highlights</h3>
      <ul className="coach-highlights">{latestResponse.highlights.map((highlight, index) => <li key={`${index}-${highlight}`}>{highlight}</li>)}</ul>
    </section>}
    <aside className="card coach-notice"><h2>Informational use</h2><p>Nutri-Box AI Coach provides general nutrition information. It is not a medical diagnosis or treatment service.</p></aside>
  </div>
}
