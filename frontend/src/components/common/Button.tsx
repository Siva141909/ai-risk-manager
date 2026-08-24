import type { ButtonHTMLAttributes, ReactNode } from 'react'
import './common.css'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'destructive'
  size?: 'sm' | 'md'
  children: ReactNode
  title?: string
}

export function Button({ variant = 'secondary', size = 'md', className, children, ...rest }: ButtonProps) {
  return (
    <button className={`btn btn-${variant} btn-${size} ${className ?? ''}`.trim()} {...rest}>
      {children}
    </button>
  )
}
