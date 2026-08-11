import { useAuth } from '../auth/useAuth'

const futureSections = ['Dashboard', 'Meals', 'Progress', 'Scan Food', 'AI Coach', 'Profile', 'Targets']

export function AppShell() {
  const { user, logout } = useAuth()
  return (
    <main className="app-shell">
      <header>
        <div><p className="eyebrow">Nutri-Box</p><h1>Welcome, {user?.first_name}</h1><p>{user?.email}</p></div>
        <button type="button" onClick={logout}>Logout</button>
      </header>
      <section aria-labelledby="future-title">
        <h2 id="future-title">Coming next</h2>
        <ul className="placeholder-grid">{futureSections.map((section) => <li key={section}>{section}</li>)}</ul>
      </section>
    </main>
  )
}
