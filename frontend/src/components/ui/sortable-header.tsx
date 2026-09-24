import type { Header } from '@tanstack/react-table'
import { ArrowUp, ArrowDown, ChevronsUpDown } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { ReactNode } from 'react'

interface SortableHeaderProps<TData, TValue> {
  header: Header<TData, TValue>
  children: ReactNode
  className?: string
}

export function SortableHeader<TData, TValue>({
  header,
  children,
  className,
}: SortableHeaderProps<TData, TValue>) {
  const sorted = header.column.getIsSorted()
  const canSort = header.column.getCanSort()

  if (!canSort) {
    return <span className={className}>{children}</span>
  }

  return (
    <button
      type="button"
      className={cn(
        'group inline-flex items-center gap-1.5 select-none rounded-sm',
        'transition-colors hover:text-foreground',
        className,
      )}
      onClick={header.column.getToggleSortingHandler()}
      title={sorted === 'asc' ? 'Ordenar descendente' : 'Ordenar ascendente'}
    >
      {children}
      {sorted === 'asc' ? (
        <ArrowUp className="h-3.5 w-3.5 text-primary" />
      ) : sorted === 'desc' ? (
        <ArrowDown className="h-3.5 w-3.5 text-primary" />
      ) : (
        <ChevronsUpDown className="h-3.5 w-3.5 opacity-40 group-hover:opacity-70" />
      )}
    </button>
  )
}