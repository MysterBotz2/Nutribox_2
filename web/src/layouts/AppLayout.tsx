import { NavLink, Outlet } from 'react-router-dom'

import { useAuth } from '../auth/useAuth'

const activeSections = [
  { to: '/app/dashboard', label: 'Dashboard' },
  { to: '/app/meals', label: 'Meals' },
  { to: '/app/progress', label: 'Progress' },
  { to: '/app/scan', label: 'Scan Food' },
  { to: '/app/profile', label: 'Profile' },
  { to: '/app/targets', label: 'Targets' },
]
const futureSections = ['AI Coach']

export function AppLayout() {
  const { user, logout } = useAuth()
  return (
    <div className="authenticated-layout">
      <aside className="sidebar">
        <div className="brand"><p className="eyebrow">Nutri-Box</p><p className="muted">Account companion</p></div>
        <nav aria-label="Main navigation">
          {activeSections.map((item) => <NavLink key={item.to} to={item.to} className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>{item.label}</NavLink>)}
          {futureSections.map((label) => <span className="nav-link disabled" key={label} aria-disabled="true">{label}<small>Coming soon</small></span>)}
        </nav>
        <div className="account-controls"><p><strong>{user?.first_name} {user?.last_name}</strong><br /><span className="muted">{user?.email}</span></p><button type="button" className="secondary-button" onClick={logout}>Logout</button></div>
      </aside>
      <main className="app-content"><Outlet /></main>
    </div>
  )
}
