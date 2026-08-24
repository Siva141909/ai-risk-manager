import type { ReactNode } from 'react'
import './layout.css'

export function PageShell({
  title,
  subtitle,
  action,
  children,
}: {
  title?: string
  subtitle?: string
  action?: ReactNode
  children: ReactNode
}) {
  return (
    <main className="page-shell">
      {(title || action) && (
        <div className="page-shell-header">
          <div>
            {title && <h1 className="page-title">{title}</h1>}
            {subtitle && <p className="page-subtitle">{subtitle}</p>}
          </div>
          {action}
        </div>
      )}
      {children}
    </main>
  )
}
