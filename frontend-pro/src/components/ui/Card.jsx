import { cn } from '@/utils/cn'

const Card = ({ children, className, hover = false, onClick }) => {
  return (
    <div
      onClick={onClick}
      className={cn(
        'bg-primary-700 border border-primary-600 rounded-lg shadow-md',
        hover && 'transition-all duration-200 hover:-translate-y-1 hover:shadow-lg hover:border-accent-blue cursor-pointer',
        className
      )}
    >
      {children}
    </div>
  )
}

const CardHeader = ({ children, className }) => (
  <div className={cn('px-6 py-4 border-b border-primary-600', className)}>
    {children}
  </div>
)

const CardTitle = ({ children, className }) => (
  <h3 className={cn('text-lg font-semibold text-text-primary', className)}>
    {children}
  </h3>
)

const CardBody = ({ children, className }) => (
  <div className={cn('px-6 py-4', className)}>
    {children}
  </div>
)

const CardDescription = ({ children, className }) => (
  <p className={cn('text-sm text-text-muted mt-1', className)}>
    {children}
  </p>
)

const CardFooter = ({ children, className }) => (
  <div className={cn('px-6 py-4 border-t border-primary-600', className)}>
    {children}
  </div>
)

Card.Header = CardHeader
Card.Title = CardTitle
Card.Description = CardDescription
Card.Body = CardBody
Card.Footer = CardFooter

export default Card

