import { NavLink, Outlet } from 'react-router-dom'
import { useEffect, useState } from 'react'

import { useAuth } from '../auth/useAuth'
import { FloatingAiChat } from '../components/FloatingAiChat'

const primarySections = [
  { to: '/app/dashboard', label: 'Home' },
  { to: '/app/meals', label: 'Meals' },
  { to: '/app/schedule', label: 'Schedule' },
  { to: '/app/progress', label: 'Progress' },
  { to: '/app/ai/chat', label: 'AI' },
  { to: '/app/profile', label: 'Profile' },
]
const secondarySections = [{ to: '/app/profile', label: 'Settings' }]

export function AppLayout() {
  const { user, logout } = useAuth()
  const [dark, setDark] = useState(() => localStorage.getItem('nutribox-theme') === 'dark')
  useEffect(() => { document.documentElement.dataset.theme = dark ? 'dark' : 'light'; localStorage.setItem('nutribox-theme', dark ? 'dark' : 'light') }, [dark])
  return (
    <div className="authenticated-layout">
      <aside className="sidebar">
        <div className="brand"><span className="brand-mark">N</span><div><strong>NutriBox</strong><p>Your nutrition companion</p></div></div>
        <nav aria-label="Primary navigation"><p className="nav-caption">Menu</p>{primarySections.map((item) => <NavLink key={item.to} to={item.to} className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>{item.label}</NavLink>)}<NavLink to="/app/coach" className={({ isActive }) => isActive ? 'nav-link ai-coach-link active' : 'nav-link ai-coach-link'}>AI Coach</NavLink></nav>
        <nav className="secondary-nav" aria-label="Secondary navigation"><p className="nav-caption">Account</p>{secondarySections.map((item) => <NavLink key={item.to} to={item.to} className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>{item.label}</NavLink>)}</nav>
        <div className="account-controls"><p><strong>{user?.first_name} {user?.last_name}</strong><span>{user?.email}</span></p><button type="button" className="theme-button" onClick={() => setDark(!dark)}>{dark ? 'Light mode' : 'Dark mode'}</button><button type="button" className="signout-button" onClick={logout}>Sign out</button></div>
      </aside>
      <main className="app-content"><header className="top-bar"><span className="muted">Your data stays in your account</span><div className="top-user"><span>{user?.first_name?.slice(0, 1) ?? 'N'}</span><strong>{user?.first_name ?? 'NutriBox'}</strong></div></header><Outlet /></main><FloatingAiChat />
    </div>
  )
}
