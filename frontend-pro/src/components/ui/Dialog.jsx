import { useEffect } from 'react'
import { X } from 'lucide-react'
import { cn } from '@/utils/cn'

const Dialog = ({ open, onOpenChange, children, className }) => {
  useEffect(() => {
    if (open) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = 'unset'
    }
    return () => {
      document.body.style.overflow = 'unset'
    }
  }, [open])

  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={() => onOpenChange(false)}
    >
      <div
        className={cn(
          'bg-primary-800 border border-primary-600 rounded-lg shadow-xl max-w-lg w-full mx-4 max-h-[90vh] overflow-y-auto',
          className
        )}
        onClick={(e) => e.stopPropagation()}
      >
        {children}
      </div>
    </div>
  )
}

const DialogContent = ({ children, className }) => (
  <div className={cn('p-6', className)}>
    {children}
  </div>
)

const DialogHeader = ({ children, className }) => (
  <div className={cn('mb-4', className)}>
    {children}
  </div>
)

const DialogTitle = ({ children, className }) => (
  <h2 className={cn('text-2xl font-bold text-text-primary', className)}>
    {children}
  </h2>
)

const DialogDescription = ({ children, className }) => (
  <p className={cn('text-sm text-text-muted mt-1', className)}>
    {children}
  </p>
)

const DialogClose = ({ onClose, className }) => (
  <button
    onClick={onClose}
    className={cn(
      'absolute top-4 right-4 text-text-muted hover:text-text-primary transition-colors',
      className
    )}
  >
    <X className="w-5 h-5" />
  </button>
)

Dialog.Content = DialogContent
Dialog.Header = DialogHeader
Dialog.Title = DialogTitle
Dialog.Description = DialogDescription
Dialog.Close = DialogClose

export default Dialog

