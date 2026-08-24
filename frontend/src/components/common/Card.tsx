import type { ReactNode } from 'react'
import './common.css'

export function Card({
  title,
  action,
  children,
  className,
}: {
  title?: string
  action?: ReactNode
  children: ReactNode
  className?: string
}) {
  return (
    <div className={`card ${className ?? ''}`.trim()}>
      {title && (
        <div className="card-header">
          <h2 className="card-title">{title}</h2>
          {action}
        </div>
      )}
      {children}
    </div>
  )
}
