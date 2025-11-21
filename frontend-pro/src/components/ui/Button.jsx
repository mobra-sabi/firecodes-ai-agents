import { cn } from '@/utils/cn'
import { Loader2 } from 'lucide-react'

const Button = ({
  children,
  className,
  variant = 'primary',
  size = 'md',
  loading = false,
  disabled = false,
  icon,
  onClick,
  type = 'button',
  ...props
}) => {
  const variants = {
    primary: 'bg-accent-blue hover:bg-accent-blue-dark text-white shadow-md hover:shadow-glow-blue',
    secondary: 'bg-transparent border-2 border-primary-600 hover:border-accent-blue text-text-primary hover:text-accent-blue',
    ghost: 'bg-transparent hover:bg-primary-700 text-text-secondary hover:text-text-primary',
    danger: 'bg-accent-red hover:bg-red-600 text-white shadow-md',
  }

  const sizes = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2 text-base',
    lg: 'px-6 py-3 text-lg',
  }

  return (
    <button
      type={type}
      disabled={disabled || loading}
      onClick={onClick}
      className={cn(
        'inline-flex items-center justify-center gap-2 font-medium rounded-md transition-all duration-200',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        'focus:outline-none focus:ring-2 focus:ring-accent-blue focus:ring-offset-2 focus:ring-offset-primary-900',
        variants[variant],
        sizes[size],
        className
      )}
      {...props}
    >
      {loading && <Loader2 className="w-4 h-4 animate-spin" />}
      {!loading && icon && <span>{icon}</span>}
      {children}
    </button>
  )
}

export default Button

