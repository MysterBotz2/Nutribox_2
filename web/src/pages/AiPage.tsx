import { NavLink, Outlet } from 'react-router-dom'

export function AiPage() {
  return <div className="page-stack"><header className="page-header"><p className="eyebrow">AI</p><h1>Nutrition support</h1><p className="muted">Chat is conversational. Coach summarizes trusted Nutri-Box data.</p></header><nav className="tabs" aria-label="AI sections"><NavLink to="chat">Chat</NavLink><NavLink to="coach">Coach</NavLink></nav><Outlet /></div>
}
