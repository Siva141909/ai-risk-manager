import { useState, type ReactNode } from 'react'
import './common.css'

export function Tooltip({ label, children }: { label: string; children: ReactNode }) {
  const [visible, setVisible] = useState(false)
  return (
    <span
      className="tooltip-wrapper"
      onMouseEnter={() => setVisible(true)}
      onMouseLeave={() => setVisible(false)}
      onFocus={() => setVisible(true)}
      onBlur={() => setVisible(false)}
    >
      {children}
      {visible && (
        <span className="tooltip-bubble" role="tooltip">
          {label}
        </span>
      )}
    </span>
  )
}
