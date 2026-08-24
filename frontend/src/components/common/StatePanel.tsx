import type { ReactNode } from 'react'
import './common.css'
import { Button } from './Button'

/**
 * One shared component for every empty/error state in the app
 * (docs/DESIGN_SYSTEM.md §5: "same component, different icon/copy/
 * action per screen — never a bespoke layout per screen").
 */
export function StatePanel({
  icon,
  title,
  description,
  actionLabel,
  onAction,
  variant = 'empty',
}: {
  icon: ReactNode
  title: string
  description?: string
  actionLabel?: string
  onAction?: () => void
  variant?: 'empty' | 'error'
}) {
  return (
    <div className={`state-panel ${variant === 'error' ? 'state-error' : ''}`} role={variant === 'error' ? 'alert' : undefined}>
      <div className="state-icon">{icon}</div>
      <div className="state-title">{title}</div>
      {description && <div>{description}</div>}
      {actionLabel && onAction && (
        <Button variant="secondary" onClick={onAction} style={{ marginTop: 'var(--space-2)' }}>
          {actionLabel}
        </Button>
      )}
    </div>
  )
}
