import { useEffect, useState } from 'react'
import { useNavigate } from '@tanstack/react-router'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { BrandLockup } from '@/components/brand'
import { MockupEnMarco, type ClaveProducto } from '@/components/landing/producto-mockup'
import {
  Zap,
  FileText,
  ArrowUpCircle,
  ArrowDownCircle,
  Building2,
  Archive,
  ScrollText,
  Menu,
  X,
  Ship,
  Bot,
  ClipboardList,
  ChevronLeft,
  ChevronRight,
  Pause,
  Play,
  BarChart3,
  TrendingUp,
  FileSpreadsheet,
  FileDown,
  MonitorDown,
  RefreshCw,
  Users,
  type LucideIcon,
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

/* ============================================================
   Productos del carrusel del hero.

   `ctas` acepta rutas internas ('/login') o URLs externas
   ('https://...'); el render distingue una de otra.
   Poner null en una entrada oculta ese boton.

   `titulo` va partido en dos lineas: la primera en blanco, la segunda con
   el degradado azul. Se guarda como par explicito y no se parte por palabras
   porque el corte automatico duplicaba la conjunction.

   OJO: la copy de PRECARGA BOT y COMANDAS PRO es un BORRADOR.
   Reemplazar `descripcion`, `puntos`, `cierre` y `ctas` por el texto real y
   la URL publica de cada producto.
   ============================================================ */
interface Producto {
  clave: ClaveProducto
  nombre: string
  /** Texto del pill superior. */
  etiqueta: string
  titulo: [string, string]
  descripcion: string
  /** Las tres filas con icono de la columna izquierda. */
  puntos: { icono: LucideIcon; titulo: string; detalle: string }[]
  /** Frase de cierre con barra azul a la izquierda. */
  cierre: string
  icono: LucideIcon
  ctas: { etiqueta: string; to: string | null }[]
}

const productos: Producto[] = [
  {
    clave: 'precarga',
    nombre: 'PreCarga',
    etiqueta: 'Dashboard en tiempo real',
    titulo: ['Control total', 'de tus operaciones'],
    descripcion:
      'Visualiza, analiza y toma decisiones con información en tiempo real. Un dashboard con la vista completa de tus operaciones marítimas.',
    puntos: [
      {
        icono: FileSpreadsheet,
        titulo: 'PDF a Excel automático',
        detalle:
          'Convierte tus solicitudes en PDF a plantillas de Excel automáticamente, listas para cargar.',
      },
      {
        icono: BarChart3,
        titulo: 'Métricas clave',
        detalle: 'Total de solicitudes, movimientos, altas, bajas y más.',
      },
      {
        icono: TrendingUp,
        titulo: 'Gráficos interactivos',
        detalle: 'Analiza tendencias y patrones en un solo vistazo.',
      },
      {
        icono: Zap,
        titulo: 'Actualización en tiempo real',
        detalle: 'Información siempre al día, sin complicaciones.',
      },
    ],
    cierre: 'Más que un dashboard, es el control de tu operación.',
    icono: Ship,
    ctas: [
      { etiqueta: 'Iniciar Sesión', to: '/login' },
      { etiqueta: 'Crear Cuenta', to: '/registro' },
    ],
  },
  {
    clave: 'bot',
    nombre: 'PreCarga Bot',
    etiqueta: 'Aplicación de escritorio',
    titulo: ['Carga alimentos al área', 'automáticamente'],
    descripcion:
      'Aplicación de escritorio para Windows que automatiza la carga de alimentos al área de tus barcos. Deja de capturarlos uno por uno.',
    puntos: [
      {
        icono: Bot,
        titulo: 'Carga automática',
        detalle: 'Sube los alimentos al área sin capturarlos a mano.',
      },
      {
        icono: MonitorDown,
        titulo: 'Para Windows',
        detalle: 'Instalador .exe: se instala y corre en tu equipo.',
      },
      {
        icono: RefreshCw,
        titulo: 'Versiones siempre al día',
        detalle: 'Descarga la última versión desde la página oficial.',
      },
    ],
    cierre: 'Más que un formulario, es un bot que trabaja por ti.',
    icono: Bot,
    ctas: [
      { etiqueta: 'Descargar para Windows', to: '/precarga-bot' },
      { etiqueta: 'Saber más', to: '/precarga-bot#versiones' },
    ],
  },
  {
    clave: 'comandas',
    nombre: 'Comandas Pro',
    etiqueta: 'Alimentación a bordo',
    titulo: ['Las comandas de cada barco', 'bajo tu control'],
    descripcion:
      'Comandas de alimentos para los trabajadores de tus barcos: registra lo que pide cada tripulación y genera reportes en PDF listos para entregar.',
    puntos: [
      {
        icono: ClipboardList,
        titulo: 'Comandas por buque',
        detalle: 'Registra cada comanda con su fecha, destino y turno.',
      },
      {
        icono: Users,
        titulo: 'Control de PAX',
        detalle: 'Distribución de pasajeros por destino, transporte y compañía.',
      },
      {
        icono: FileDown,
        titulo: 'Reportes en PDF',
        detalle: 'Reporte estadístico listo para compartir, con el detalle por compañía.',
      },
    ],
    cierre: 'Más que una comanda, es el control de la alimentación a bordo.',
    icono: ClipboardList,
    ctas: [
      { etiqueta: 'Ir a Comandas Pro', to: 'https://comandas-opq6.onrender.com' },
      { etiqueta: 'Saber más', to: '#acerca' },
    ],
  },
]

// Milisegundos que cada slide queda en pantalla antes de avanzar solo.
const MS_SLIDE = 7000

export default function Landing() {
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)
  const [indice, setIndice] = useState(0)
  const [pausado, setPausado] = useState(false)

  const producto = productos[indice]

  const irA = (i: number) => setIndice((i + productos.length) % productos.length)

  // Un cambio en el indice reinicia el temporizador: si el usuario avanza a
  // mano, tiene que ver el slide completo, no quedar con 2 s de lectura.
  //
  // prefers-reduced-motion tambien desactiva el avance automatico: en el hero
  // el texto cambia solo y ese movimiento es justo lo que el usuario pidio
  // evitar. Los controles manuales siguen funcionando.
  useEffect(() => {
    if (pausado) return
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    const t = setTimeout(() => setIndice((i) => (i + 1) % productos.length), MS_SLIDE)
    return () => clearTimeout(t)
  }, [indice, pausado])

  const go = (to: string, hash?: string) => {
    setMenuOpen(false)
    navigate({ to, hash: hash || undefined })
  }

  // Los CTA del carrusel tienen cuatro destinos posibles: URL externa (se abre
  // en otra pestana), ancla de esta pagina (#seccion), ruta del router, o ruta
  // con ancla ('/precarga-bot#versiones'). Sin los dos ultimos casos,
  // navigate() los interpretaria como una ruta incompleta.
  const Cta = ({ etiqueta, to }: { etiqueta: string; to: string | null }) => {
    if (!to) return null

    if (/^https?:\/\//.test(to)) {
      return (
        <Button size="lg" className="gap-2 px-7" asChild>
          <a href={to} target="_blank" rel="noreferrer noopener">
            {etiqueta}
          </a>
        </Button>
      )
    }

    if (to.startsWith('#')) {
      return (
        <Button size="lg" variant="outline" className="gap-2 px-7" asChild>
          <a href={to}>{etiqueta}</a>
        </Button>
      )
    }

    const [ruta, ancla] = to.split('#')

    return (
      <Button size="lg" className="gap-2 px-7" onClick={() => go(ruta, ancla)}>
        {etiqueta}
      </Button>
    )
  }

  return (
    <div className="flex min-h-screen flex-col scroll-smooth">
      <header className="sticky top-0 z-50 flex items-center justify-between border-b border-border/50 bg-background/80 px-4 py-3 backdrop-blur-xl sm:px-6">
        <a href="#inicio" className="flex items-center">
          <BrandLockup className="h-10 sm:h-12" />
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
        {/* El hero lleva su propio fondo azul, distinto del tema neutro del
            resto de la pagina: es lo que separa la promesa del producto del
            contenido institucional de abajo. */}
        <section
          id="inicio"
          className="relative isolate flex flex-col overflow-hidden px-6 pb-14 pt-14 lg:min-h-[94vh] lg:justify-center lg:pb-20 lg:pt-20"
        >
          <div className="pointer-events-none absolute inset-0 -z-10 bg-[#070d1c]" />
          <div className="pointer-events-none absolute inset-0 -z-10 bg-gradient-to-b from-[#0c1a3d] via-[#081227] to-[#070d1c]" />
          <div className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_78%_22%,rgba(37,99,235,0.42),transparent_58%)]" />
          <div className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_6%_88%,rgba(124,58,237,0.30),transparent_58%)]" />

          {/* El logo ya no se repite en el centro del hero: la marca vive solo
              en el encabezado y duplicarla compite con el titulo del producto,
              que es lo que el visitante tiene que leer primero. */}
          <div className="relative mx-auto w-full max-w-7xl">
            {/* Carrusel de productos.

                SIN aria-live a proposito: el slide entero (pill, titulo, 3
                filas y 2 botones) se anunciaria en cada cambio y un lector de
                pantalla no puede saltarse un anuncio largo con la barra
                espaciadora. El avance automatico se pausa ademas con el boton de
                play/pausa, que es lo que pide WCAG 2.2.2 para contenido que se
                actualiza solo.

                La key del <div> interior reinicia la animacion de entrada. */}
            <div
              key={indice}
              className="fluent-anim-fade"
              role="group"
              aria-roledescription="carrusel"
              aria-label="Nuestros productos"
            >
              {/* El grid arranca en lg: en pantallas anchas la captura se va a
                  la derecha y el texto a la izquierda, como en el diseno de
                  referencia. Por debajo de lg se apilan con el texto primero. */}
              {/* Reparto 0.95/1.05 en vez de 0.82/1.18: la captura de Comandas Pro es
                  apaisada (2.11:1) y con la columna mas angosta quedaba baja
                  frente al bloque de texto. */}
              <div className="grid items-center gap-12 lg:grid-cols-[0.95fr_1.05fr] lg:gap-14">
                {/* ---------------- columna de texto ---------------- */}
                <div className="flex flex-col items-center text-center lg:items-start lg:text-left">
                  {/* pill: icono + etiqueta del producto, con el contador como
                      sufijo para que se sepa cuantos hay */}
                  <span className="inline-flex items-center gap-2 rounded-full border border-primary/40 bg-primary/10 px-4 py-1.5 text-[13px] font-medium text-white">
                    <producto.icono className="h-4 w-4 text-primary" />
                    {producto.etiqueta}
                    <span className="text-white/45">
                      {indice + 1}/{productos.length}
                    </span>
                  </span>

                  <h1 className="mt-6 text-[2.6rem] font-extrabold leading-[1.04] tracking-tight text-white sm:text-6xl">
                    {producto.titulo[0]}
                    <span className="block bg-gradient-to-r from-[#7dd3fc] via-[#38bdf8] to-[#818cf8] bg-clip-text text-transparent">
                      {producto.titulo[1]}
                    </span>
                  </h1>

                  <p className="mt-5 max-w-lg text-base leading-relaxed text-muted-foreground sm:text-lg">
                    {producto.descripcion}
                  </p>

                  {/* las tres filas con icono del diseno de referencia */}
                  <ul className="mt-8 grid w-full max-w-lg gap-5">
                    {producto.puntos.map((p) => {
                      const Icono = p.icono
                      return (
                        <li key={p.titulo} className="flex items-start gap-4 text-left">
                          <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary/15 ring-1 ring-inset ring-primary/25">
                            <Icono className="h-5 w-5 text-[#38bdf8]" />
                          </span>
                          <span className="min-w-0">
                            <span className="block text-[15px] font-semibold text-white">
                              {p.titulo}
                            </span>
                            <span className="mt-0.5 block text-sm leading-relaxed text-muted-foreground">
                              {p.detalle}
                            </span>
                          </span>
                        </li>
                      )
                    })}
                  </ul>

                  {/* cierre con barra azul */}
                  <p className="mt-9 max-w-lg border-l-2 border-primary pl-4 text-left text-[15px] leading-relaxed text-muted-foreground">
                    {producto.cierre.split(',')[0]},
                    <span className="mt-0.5 block font-semibold text-[#7dd3fc]">
                      {producto.cierre.slice(producto.cierre.indexOf(',') + 1).trim()}
                    </span>
                  </p>

                  <div className="mt-8 flex flex-wrap items-center justify-center gap-3 lg:justify-start">
                    {producto.ctas.map((cta) => (
                      <Cta key={cta.etiqueta} {...cta} />
                    ))}
                  </div>
                </div>

                {/* ---------------- columna de la captura ---------------- */}
                {/* Tope de ancho en movil: sin el, el SVG escalaria a 900px+ y la
                    captura se comeria el alto del slide, empujando los controles
                    fuera de pantalla. */}
                <div className="relative mx-auto w-full max-w-[21rem] sm:max-w-lg lg:max-w-none">
                  {/* resplandor detras del marco, del mismo azul del diseno */}
                  <div className="pointer-events-none absolute -inset-6 -z-10 rounded-[2rem] bg-[radial-gradient(ellipse_at_center,rgba(0,120,212,0.35),transparent_70%)]" />
                  <MockupEnMarco clave={producto.clave} />
                </div>
              </div>
            </div>

            {/* Controles. Se quedan visibles siempre: sin avance manual el
                carrusel es solo decoracion y no hay forma de volver atras. */}
            <div className="mt-9 flex items-center justify-center gap-5 lg:mt-10">
              <button
                type="button"
                aria-label="Producto anterior"
                onClick={() => irA(indice - 1)}
                className="flex h-9 w-9 items-center justify-center rounded-full border border-border/50 bg-background/40 text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>

              <div className="flex items-center gap-2.5">
                {productos.map((p, i) => (
                  <button
                    key={p.clave}
                    type="button"
                    aria-label={`Producto ${i + 1} de ${productos.length}: ${p.nombre}`}
                    aria-current={i === indice}
                    onClick={() => irA(i)}
                    onMouseEnter={() => setPausado(true)}
                    onMouseLeave={() => setPausado(false)}
                    className={cn(
                      'h-2 rounded-full transition-all duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background',
                      i === indice
                        ? 'w-8 bg-primary'
                        : 'w-2 bg-muted-foreground/35 hover:bg-muted-foreground/60',
                    )}
                  />
                ))}
              </div>

              {/* WCAG 2.2.2: el avance automatico tiene que poder detenerse.
                  Sin este boton el texto que rota solo no tiene pausa. */}
              <button
                type="button"
                aria-label={pausado ? 'Reanudar avance automático' : 'Pausar avance automático'}
                onClick={() => setPausado((p) => !p)}
                className="flex h-9 w-9 items-center justify-center rounded-full border border-border/50 bg-background/40 text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                {pausado ? <Play className="h-4 w-4" /> : <Pause className="h-4 w-4" />}
              </button>

              <button
                type="button"
                aria-label="Producto siguiente"
                onClick={() => irA(indice + 1)}
                className="flex h-9 w-9 items-center justify-center rounded-full border border-border/50 bg-background/40 text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
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
            <h2 className="text-center text-3xl font-bold tracking-tight">Acerca de PreCarga</h2>

            <div className="mt-12 grid items-center gap-12 lg:grid-cols-2">
              <div>
                <p className="mb-4 text-muted-foreground">
                  Precarga es una herramienta especializada diseñada para optimizar el
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
                  diferenciados, y generación automática de documentos, Precarga es la
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
        © 2026 PreCarga · Desarrollado por <span className="text-primary">Angel Valenzuela</span>
      </footer>
    </div>
  )
}