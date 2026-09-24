import { useState } from 'react'
import { useNavigate } from '@tanstack/react-router'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import {
  Ship,
  Zap,
  FileText,
  ArrowUpCircle,
  ArrowDownCircle,
  Building2,
  Archive,
  ScrollText,
  Menu,
  X,
} from 'lucide-react'

const features = [
  {
    title: 'Procesamiento de PDFs',
    description:
      'Extrae automáticamente información de documentos PDF y genera archivos Excel listos para usar.',
    icon: FileText,
  },
  {
    title: 'Gestión de Altas',
    description:
      'Registra y administra la entrada de nuevos activos al sistema con validaciones automáticas.',
    icon: ArrowUpCircle,
  },
  {
    title: 'Gestión de Bajas',
    description:
      'Controla la salida de activos y mantén un registro histórico completo de cada operación.',
    icon: ArrowDownCircle,
  },
  {
    title: 'Catálogo de Compañías',
    description:
      'Base de datos centralizada de compañías y proveedores para agilizar el registro.',
    icon: Building2,
  },
  {
    title: 'Catálogo de Activos',
    description:
      'Inventario completo de activos con búsqueda rápida y filtros avanzados.',
    icon: Archive,
  },
  {
    title: 'Logs y Auditoría',
    description:
      'Registro detallado de todas las operaciones realizadas para trazabilidad completa.',
    icon: ScrollText,
  },
]

const stats = [
  { value: '99%', label: 'Precisión' },
  { value: '10x', label: 'Más rápido' },
  { value: '24/7', label: 'Disponibilidad' },
  { value: '100%', label: 'Trazable' },
]

export default function Landing() {
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)

  const go = (to: string) => {
    setMenuOpen(false)
    navigate({ to })
  }

  return (
    <div className="flex min-h-screen flex-col scroll-smooth">
      <header className="sticky top-0 z-50 flex items-center justify-between border-b border-border/50 bg-background/80 px-4 py-3 backdrop-blur-xl sm:px-6">
        <a href="#inicio" className="flex items-center gap-2">
          <Ship className="h-6 w-6 text-primary" />
          <span className="text-lg font-semibold tracking-tight">PreCarga SHAT</span>
        </a>

        <nav className="hidden items-center gap-6 md:flex">
          <a
            href="#inicio"
            className="text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
          >
            Inicio
          </a>
          <a
            href="#caracteristicas"
            className="text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
          >
            Características
          </a>
          <a
            href="#acerca"
            className="text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
          >
            Acerca de
          </a>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={() => go('/login')}>
              Iniciar Sesión
            </Button>
            <Button size="sm" onClick={() => go('/registro')}>
              Registrarse
            </Button>
          </div>
        </nav>

        <button
          type="button"
          className="flex h-8 w-8 items-center justify-center rounded-md text-foreground hover:bg-[rgb(255_255_255_/_0.06)] md:hidden"
          aria-label="Menú"
          onClick={() => setMenuOpen((o) => !o)}
        >
          {menuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </header>

      {menuOpen && (
        <div className="flex flex-col gap-3 border-b border-border/50 bg-background/95 px-6 py-4 backdrop-blur-xl md:hidden">
          {['inicio', 'caracteristicas', 'acerca'].map((id) => (
            <a
              key={id}
              href={`#${id}`}
              className="text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
              onClick={() => setMenuOpen(false)}
            >
              {id === 'inicio'
                ? 'Inicio'
                : id === 'caracteristicas'
                  ? 'Características'
                  : 'Acerca de'}
            </a>
          ))}
          <div className="flex gap-2 pt-2">
            <Button variant="outline" className="flex-1" onClick={() => go('/login')}>
              Iniciar Sesión
            </Button>
            <Button className="flex-1" onClick={() => go('/registro')}>
              Registrarse
            </Button>
          </div>
        </div>
      )}

      <main className="flex-1">
        <section
          id="inicio"
          className="relative flex min-h-[90vh] flex-col items-center justify-center overflow-hidden px-6 py-24 text-center"
        >
          <div className="absolute inset-0 bg-gradient-to-b from-primary/10 via-primary/5 to-background" />
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-primary/15 via-transparent to-transparent" />

          <div className="relative">
            <Badge variant="accent" className="gap-1.5 px-3 py-1 text-[12.5px]">
              <Zap className="h-3.5 w-3.5" />
              Sistema de Gestión de Activos
            </Badge>

            <h1 className="mt-6 max-w-4xl text-4xl font-extrabold tracking-tight sm:text-5xl lg:text-6xl">
              Gestiona tus activos
              <span className="block bg-gradient-to-r from-white via-white to-[hsl(206_100%_72%)] bg-clip-text text-transparent">
                de forma inteligente
              </span>
            </h1>

            <p className="mx-auto mt-5 max-w-2xl text-lg text-muted-foreground sm:text-xl">
              Sistema web para procesamiento de documentos de alta y baja de activos.
              <br className="hidden sm:block" /> Optimizado para Logística Marina PEMEX.
            </p>

            <div className="mt-9 flex flex-wrap items-center justify-center gap-4">
              <Button size="lg" className="gap-2 px-7" onClick={() => go('/login')}>
                Iniciar Sesión
              </Button>
              <Button size="lg" variant="outline" className="gap-2 px-7" onClick={() => go('/registro')}>
                Crear Cuenta
              </Button>
            </div>
          </div>
        </section>

        <section
          id="caracteristicas"
          className="scroll-mt-20 border-t border-border/50 bg-[rgb(255_255_255_/_0.02)] px-6 py-20"
        >
          <div className="mx-auto max-w-6xl">
            <div className="mb-12 text-center">
              <h2 className="text-3xl font-bold tracking-tight">Características principales</h2>
              <p className="mt-2 text-muted-foreground">
                Todo lo que necesitas para gestionar el personal marítimo en un solo lugar.
              </p>
            </div>

            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {features.map((feature) => {
                const Icon = feature.icon
                return (
                  <Card
                    key={feature.title}
                    className={cn(
                      'group relative overflow-hidden transition-colors hover:border-primary/30',
                    )}
                  >
                    <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-transparent opacity-0 transition-opacity group-hover:opacity-100" />
                    <CardContent className="relative p-6">
                      <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                        <Icon className="h-5 w-5 text-primary" />
                      </div>
                      <h3 className="mb-2 font-semibold">{feature.title}</h3>
                      <p className="text-sm text-muted-foreground">{feature.description}</p>
                    </CardContent>
                  </Card>
                )
              })}
            </div>
          </div>
        </section>

        <section id="acerca" className="scroll-mt-20 border-t border-border/50 px-6 py-20">
          <div className="mx-auto max-w-6xl">
            <h2 className="text-center text-3xl font-bold tracking-tight">Acerca de PreCarga SHAT</h2>

            <div className="mt-12 grid items-center gap-12 lg:grid-cols-2">
              <div>
                <p className="mb-4 text-muted-foreground">
                  Precarga SHAT es una herramienta especializada diseñada para optimizar el
                  proceso de gestión de activos en el sector energético. Nuestro sistema
                  automatiza la extracción de datos de documentos PDF y facilita la generación de
                  reportes en formato Excel.
                </p>
                <p className="mb-4 text-muted-foreground">
                  Desarrollado específicamente para las operaciones de Logística Marina de PEMEX,
                  el sistema garantiza precisión, rapidez y trazabilidad en cada operación de alta
                  o baja de activos.
                </p>
                <p className="mb-4 text-muted-foreground">
                  Con una interfaz moderna y amigable, acceso multiusuario con roles
                  diferenciados, y generación automática de documentos, Precarga SHAT es la
                  solución ideal para la gestión eficiente de activos empresariales.
                </p>

                <div className="mt-8 grid grid-cols-2 gap-4 sm:grid-cols-4 lg:grid-cols-2 xl:grid-cols-4">
                  {stats.map((stat) => (
                    <Card
                      key={stat.label}
                      className="p-4 text-center transition-colors hover:border-primary/30"
                    >
                      <span className="block text-3xl font-extrabold text-primary">
                        {stat.value}
                      </span>
                      <span className="mt-1 block text-xs text-muted-foreground">{stat.label}</span>
                    </Card>
                  ))}
                </div>
              </div>

              <div className="order-first lg:order-none">
                <Card className="overflow-hidden">
                  <img
                    src="/tanker_ship.svg"
                    alt="Barco petrolero en operaciones offshore"
                    className="block h-auto w-full"
                  />
                </Card>
              </div>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-border/50 px-6 py-6 text-center text-sm text-muted-foreground">
        © 2026 PreCarga SHAT · Desarrollado por <span className="text-primary">Angel Valenzuela</span>
      </footer>
    </div>
  )
}