import { NavLink, Outlet } from 'react-router-dom'
import { useEffect, useState } from 'react'

import { useAuth } from '../auth/useAuth'

const activeSections = [
  { to: '/app/dashboard', label: 'Home' },
  { to: '/app/meals', label: 'Meals' },
  { to: '/app/schedule', label: 'Schedule' },
  { to: '/app/progress', label: 'Progress' },
  { to: '/app/ai/chat', label: 'AI Chat' },
  { to: '/app/coach', label: 'AI Coach' },
  { to: '/app/profile', label: 'Profile' },
  { to: '/app/devices', label: 'Devices' },
  { to: '/app/targets', label: 'Targets' },
]
const futureSections: string[] = []

export function AppLayout() {
  const { user, logout } = useAuth()
  const [dark, setDark] = useState(() => localStorage.getItem('nutribox-theme') === 'dark')
  useEffect(() => { document.documentElement.dataset.theme = dark ? 'dark' : 'light'; localStorage.setItem('nutribox-theme', dark ? 'dark' : 'light') }, [dark])
  return (
    <div className="authenticated-layout">
      <aside className="sidebar">
        <div className="brand"><p className="eyebrow">Nutri-Box</p><p className="muted">Your nutrition companion</p></div>
        <nav aria-label="Main navigation">
          {activeSections.map((item) => <NavLink key={item.to} to={item.to} className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>{item.label}</NavLink>)}
          {futureSections.map((label) => <span className="nav-link disabled" key={label} aria-disabled="true">{label}<small>Coming soon</small></span>)}
        </nav>
        <div className="account-controls"><p><strong>{user?.first_name} {user?.last_name}</strong><br /><span className="muted">{user?.email}</span></p><button type="button" className="secondary-button" onClick={() => setDark(!dark)}>{dark ? 'Light mode' : 'Dark mode'}</button><button type="button" className="secondary-button" onClick={logout}>Logout</button></div>
      </aside>
      <main className="app-content"><header className="top-bar"><strong>Nutri-Box</strong><span className="muted">Your data stays in your account</span></header><Outlet /></main>
    </div>
  )
}
