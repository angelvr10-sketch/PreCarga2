import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

/* ============================================================
   Windows 11 Fluent UI Badge
   ============================================================ */
const badgeVariants = cva(
  [
    'inline-flex items-center gap-1 rounded px-1.5 py-0.5',
    'text-[11.5px] font-semibold leading-none',
    'border transition-colors',
  ].join(' '),
  {
    variants: {
      variant: {
        // Accent - solid Windows blue
        accent:
          'bg-primary/15 text-[hsl(206_100%_75%)] border-primary/30',
        // Subtle - neutral surface
        subtle:
          'bg-[rgb(255_255_255_/_0.06)] text-foreground border-[rgb(255_255_255_/_0.10)]',
        // Outline
        outline: 'bg-transparent text-foreground border-[rgb(255_255_255_/_0.18)]',
        // Destructive
        destructive:
          'bg-destructive/15 text-[hsl(0_80%_75%)] border-destructive/30',
        // Success
        success:
          'bg-[hsl(141_60%_48%_/_0.15)] text-[hsl(141_60%_70%)] border-[hsl(141_60%_48%_/_0.30)]',
        // Warning
        warning:
          'bg-[hsl(38_95%_53%_/_0.15)] text-[hsl(38_95%_70%)] border-[hsl(38_95%_53%_/_0.30)]',
        // Legacy aliases
        default: '',
        secondary: '',
      },
    },
    defaultVariants: {
      variant: 'subtle',
    },
  },
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />
}

export { Badge, badgeVariants }
