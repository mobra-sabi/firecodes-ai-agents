import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

// Utility for merging Tailwind classes
export function cn(...inputs) {
  return twMerge(clsx(inputs))
}

