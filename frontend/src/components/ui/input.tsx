import * as React from 'react'
import { cn } from '@/lib/utils'

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          'flex h-8 w-full rounded-md px-3 text-[13.5px] font-normal',
          'bg-[rgb(255_255_255_/_0.04)] text-foreground',
          'border border-[rgb(255_255_255_/_0.10)]',
          'placeholder:text-muted-foreground/70',
          'transition-colors duration-100',
          'hover:bg-[rgb(255_255_255_/_0.06)] hover:border-[rgb(255_255_255_/_0.14)]',
          'focus-visible:outline-none focus-visible:bg-[rgb(255_255_255_/_0.06)]',
          'focus-visible:border-primary focus-visible:ring-2 focus-visible:ring-primary/30',
          'disabled:cursor-not-allowed disabled:opacity-40',
          'file:border-0 file:bg-transparent file:text-sm file:font-medium',
          className,
        )}
        ref={ref}
        {...props}
      />
    )
  },
)
Input.displayName = 'Input'

export { Input }
