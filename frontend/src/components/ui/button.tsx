import * as React from 'react'
import { Slot } from '@radix-ui/react-slot'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

/* ============================================================
   Windows 11 Fluent UI Button
   - 32px height default
   - 4-6px radius
   - Subtle borders, focus ring 2px
   ============================================================ */
const buttonVariants = cva(
  [
    'inline-flex items-center justify-center gap-1.5 whitespace-nowrap select-none',
    'rounded-md text-[13.5px] font-semibold',
    'transition-colors duration-100',
    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background',
    'disabled:pointer-events-none disabled:opacity-40',
    '[&_svg]:pointer-events-none [&_svg]:shrink-0',
  ].join(' '),
  {
    variants: {
      variant: {
        // Accent - Primary CTA (Windows blue)
        accent:
          'bg-primary text-primary-foreground border border-primary ' +
          'hover:bg-[hsl(206_100%_45%)] active:bg-[hsl(206_100%_38%)] ' +
          'shadow-fluent-1',

        // Standard - Subtle filled neutral (Win11 secondary)
        standard:
          'bg-[rgb(255_255_255_/_0.06)] text-foreground border border-[rgb(255_255_255_/_0.08)] ' +
          'hover:bg-[rgb(255_255_255_/_0.10)] active:bg-[rgb(255_255_255_/_0.04)]',

        // Outline - Border only
        outline:
          'bg-transparent text-foreground border border-[rgb(255_255_255_/_0.12)] ' +
          'hover:bg-[rgb(255_255_255_/_0.05)] active:bg-[rgb(255_255_255_/_0.02)]',

        // Subtle - Transparent, fills on hover (Win11 low-emphasis)
        subtle:
          'bg-transparent text-foreground border border-transparent ' +
          'hover:bg-[rgb(255_255_255_/_0.06)] active:bg-[rgb(255_255_255_/_0.03)]',

        // Ghost - No background at all
        ghost:
          'bg-transparent text-foreground border border-transparent ' +
          'hover:bg-[rgb(255_255_255_/_0.04)]',

        // Destructive
        destructive:
          'bg-destructive text-destructive-foreground border border-destructive ' +
          'hover:bg-[hsl(0_72%_45%)] active:bg-[hsl(0_72%_40%)] shadow-fluent-1',

        // Hyperlink
        link:
          'bg-transparent text-primary border border-transparent underline-offset-4 ' +
          'hover:underline rounded-sm px-0 h-auto',

        // Legacy aliases (keep API compat)
        default: '',
        secondary: '',
      },
      size: {
        sm: 'h-7 px-2.5 text-[12.5px] [&_svg]:h-3.5 [&_svg]:w-3.5',
        default: 'h-8 px-3.5 [&_svg]:h-4 [&_svg]:w-4',
        lg: 'h-10 px-5 text-[14.5px] [&_svg]:h-[18px] [&_svg]:w-[18px]',
        icon: 'h-8 w-8 px-0 [&_svg]:h-4 [&_svg]:w-4',
        'icon-sm': 'h-7 w-7 px-0 [&_svg]:h-3.5 [&_svg]:w-3.5',
      },
    },
    defaultVariants: {
      variant: 'accent',
      size: 'default',
    },
  },
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : 'button'
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    )
  },
)
Button.displayName = 'Button'

export { Button, buttonVariants }
