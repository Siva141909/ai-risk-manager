import { NavLink } from 'react-router-dom'
import './layout.css'

export function TopNav() {
  return (
    <header className="top-nav">
      <div className="top-nav-brand">AI Risk Manager</div>
      <nav className="top-nav-links">
        <NavLink to="/" end className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>
          Risk Overview
        </NavLink>
        <NavLink to="/cases" className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>
          Case Queue
        </NavLink>
      </nav>
      {/* Dev tooling, not part of the product surface — visually
          de-emphasized and separated from the two primary nav items above
          (docs/FRONTEND_UX.md: "not a product nav item"). */}
      <NavLink to="/demo" className="nav-link-dev">
        Demo Mode
      </NavLink>
    </header>
  )
}
