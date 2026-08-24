import type { ReactNode } from 'react'
import './common.css'

export function Badge({ variant, children }: { variant: string; children: ReactNode }) {
  return <span className={`badge ${variant}`}>{children}</span>
}
