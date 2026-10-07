import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { BrandLockup } from '@/components/brand'
import {
  Bot,
  MonitorDown,
  RefreshCw,
  ShieldCheck,
  Zap,
  Check,
  ExternalLink,
  ArrowLeft,
  FlaskConical,
} from 'lucide-react'

/* ============================================================
   Pagina de PreCarga Bot.

   Estatica a proposito: no pide sesion ni consulta la API, asi que se puede
   publicar como HTML plano si algun dia se quiere separar de este proyecto.

   El proyecto esta en BETA 1 y todavia no hay instalador publico, asi que
   no hay descargas: por eso las CTAs abren un aviso de "proximamente" en vez
   de enlazar a un .exe.

   QUE HAY QUE TOCAR PARA PUBLICAR LA PRIMERA BETA:
     - poner'se VERSION.salida = false para quitar el aviso
     - poner el .exe en /public/descargas y habilitar el campo `archivo`
     - revisar que los `cambios` sean los de la entrega real
   ============================================================ */

interface Version {
  /** Etiqueta visible. Es la que va en la tarjeta y en el pie. */
  numero: string
  /** Si es false, la pagina muestra el aviso de "proximamente". */
  salida: boolean
  /** Ruta del .exe. Solo se usa cuando `salida` es true. */
  archivo: string | null
  peso: string
  cambios: string[]
}

const VERSION: Version = {
  numero: 'Beta 1',
  salida: false,
  archivo: null,
  peso: '18 MB aprox.',
  cambios: [
    'Carga automática de los alimentos al área de cada embarcación.',
    'Bitácora de la carga con cada registro enviado.',
    'Progreso por comanda, con la posibilidad de pausar y reanudar.',
  ],
}

const PUNTOS = [
  {
    icono: Zap,
    titulo: 'Carga automática',
    detalle: 'Sube los alimentos al área sin capturarlos uno por uno.',
  },
  {
    icono: MonitorDown,
    titulo: 'Aplicación de escritorio',
    detalle: 'Corre en tu equipo con Windows 10 o superior.',
  },
  {
    icono: RefreshCw,
    titulo: 'Versiones al día',
    detalle: 'Esta página siempre muestra la última versión disponible.',
  },
  {
    icono: ShieldCheck,
    titulo: 'Tus datos siguen aquí',
    detalle: 'El bot no manda nada a ningún lado: sube directo al sitio.',
  },
]

export default function PreCargaBot() {
  const disponible = VERSION.salida && VERSION.archivo !== null
  const archivo = VERSION.archivo

  return (
    <div className="flex min-h-screen flex-col bg-[#070d1c]">
      {/* ---------------- encabezado ---------------- */}
      <header className="sticky top-0 z-50 border-b border-white/10 bg-[#070d1c]/85 backdrop-blur-xl">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-3">
          <a href="/" className="flex items-center">
            <BrandLockup className="h-9 sm:h-10" />
          </a>
          <Button variant="outline" size="sm" asChild>
            <a href="/">
              <ArrowLeft className="h-3.5 w-3.5" />
              Volver a PreCarga
            </a>
          </Button>
        </div>
      </header>

      <main className="flex-1">
        {/* ---------------- heroe ---------------- */}
        <section className="relative isolate overflow-hidden px-6 pb-16 pt-16 text-center sm:pt-20">
          <div className="pointer-events-none absolute inset-0 -z-10 bg-[#0c1a3d]/60" />
          <div className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_50%_0%,rgba(37,99,235,0.35),transparent_62%)]" />

          <div className="mx-auto max-w-3xl">
            <span className="inline-flex items-center gap-2 rounded-full border border-primary/40 bg-primary/10 px-4 py-1.5 text-[14px] font-medium text-white">
              <Bot className="h-4 w-4 text-[#38bdf8]" />
              Aplicación de escritorio para Windows
            </span>

            <h1 className="mt-6 text-4xl font-extrabold leading-[1.06] tracking-tight text-white sm:text-5xl">
              PreCarga Bot
              <span className="block bg-gradient-to-r from-[#7dd3fc] via-[#38bdf8] to-[#818cf8] bg-clip-text text-transparent">
                carga los alimentos al área
              </span>
            </h1>

            <p className="mx-auto mt-5 max-w-xl text-lg text-slate-300">
              Automatiza la carga de alimentos al área de tus barcos y deja de
              capturarlos uno por uno.
            </p>

            {/* Aviso de "proximamente". Es lo unico que hay en lugar del
                boton de descarga mientras no exista instalador publico. */}
            {!disponible && (
              <div className="mx-auto mt-9 max-w-md rounded-xl border border-amber-400/30 bg-amber-400/10 px-6 py-5">
                <p className="flex items-center justify-center gap-2 text-sm font-semibold uppercase tracking-wider text-amber-300">
                  <FlaskConical className="h-4 w-4" />
                  Próximamente
                </p>
                <p className="mt-2 text-sm leading-relaxed text-slate-300">
                  Estamos en <span className="font-semibold text-white">Beta 1</span>.
                  El instalador todavía no está disponible para descarga.
                </p>
              </div>
            )}

            {disponible && archivo && (
              <div className="mt-9 flex flex-wrap items-center justify-center gap-3">
                <Button size="lg" className="gap-2 px-7" asChild>
                  <a href={archivo} download>
                    Descargar {VERSION.numero}
                  </a>
                </Button>
              </div>
            )}

            <p className="mt-5 text-sm text-slate-400">
              Versión actual: {VERSION.numero} · {VERSION.peso}
            </p>
          </div>

          {/* Captura de la app trabajando. Va en un marco inclinado porque en
              plano deadouriaria el ritmo de la pagina; el marco lo ancla a la
              columna de texto y evita que el heroe quede como un bloque de
              texto sobre el fondo. */}
          <div className="relative mx-auto mt-14 max-w-5xl">
            {/* resplandor detras, del mismo azul del resto del sitio */}
            <div className="pointer-events-none absolute -inset-x-6 -top-4 bottom-0 -z-10 rounded-[2rem] bg-[radial-gradient(ellipse_at_60%_40%,rgba(0,120,212,0.35),transparent_68%)]" />

            <div className="overflow-hidden rounded-2xl border border-primary/40 shadow-[0_0_0_1px_rgba(0,120,212,0.22),0_30px_80px_-20px_rgba(0,120,212,0.6)]">
              <img
                src="/precarga-bot.webp"
                alt="PreCarga Bot: un robot procesa archivos de Excel y PDF mientras el tablero muestra el avance al 68%. El progreso detalle que esta leyendo el archivo Excel, extrayendo los datos del PDF, validando la informacion y guardandola en la base de datos."
                width={1536}
                height={1024}
                loading="lazy"
                decoding="async"
                className="block h-auto w-full"
              />
            </div>
          </div>
        </section>

        {/* ---------------- qué hace ---------------- */}
        <section className="border-t border-white/10 px-6 py-16">
          <div className="mx-auto max-w-6xl">
            <h2 className="text-center text-2xl font-bold text-white sm:text-3xl">
              Qué hace el bot
            </h2>

            <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
              {PUNTOS.map((p) => {
                const Icono = p.icono
                return (
                  <Card
                    key={p.titulo}
                    className="border-white/10 bg-white/[0.04] transition-colors hover:border-primary/40"
                  >
                    <CardContent className="p-5">
                      <span className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-primary/15 ring-1 ring-inset ring-primary/25">
                        <Icono className="h-5 w-5 text-[#38bdf8]" />
                      </span>
                      <h3 className="mb-1 font-semibold text-white">{p.titulo}</h3>
                      <p className="text-sm text-slate-400">{p.detalle}</p>
                    </CardContent>
                  </Card>
                )
              })}
            </div>
          </div>
        </section>

        {/* ---------------- versión actual ---------------- */}
        <section
          id="versiones"
          className="scroll-mt-20 border-t border-white/10 bg-white/[0.02] px-6 py-16"
        >
          <div className="mx-auto max-w-2xl">
            <h2 className="text-center text-2xl font-bold text-white sm:text-3xl">
              Versión actual
            </h2>

            <Card className="mt-10 border-primary/50 bg-primary/[0.07]">
              <CardContent className="p-6">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="text-lg font-bold text-white">
                        Versión {VERSION.numero}
                      </h3>
                      <span className="rounded-full border border-amber-400/40 bg-amber-400/15 px-2 py-0.5 text-[11.5px] font-semibold text-amber-300">
                        En pruebas
                      </span>
                    </div>
                    <p className="mt-0.5 text-sm text-slate-400">
                      {VERSION.peso}
                    </p>
                  </div>

                  {disponible && archivo && (
                    <Button className="gap-2" asChild>
                      <a href={archivo} download>
                        Descargar
                      </a>
                    </Button>
                  )}
                </div>

                <ul className="mt-5 grid gap-2">
                  {VERSION.cambios.map((c) => (
                    <li key={c} className="flex items-start gap-2 text-sm text-slate-300">
                      <Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#38bdf8]" />
                      <span>{c}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          </div>
        </section>

        {/* ---------------- requisitos ---------------- */}
        <section className="border-t border-white/10 px-6 py-16">
          <div className="mx-auto max-w-4xl">
            <h2 className="text-center text-2xl font-bold text-white sm:text-3xl">
              Requisitos
            </h2>
            <ul className="mx-auto mt-8 grid max-w-xl gap-3">
              {[
                'Windows 10 o superior (64 bits).',
                'Conexión a internet durante la carga.',
                'Permiso de escritura en la carpeta que elijas para el archivo de registros.',
              ].map((r) => (
                <li key={r} className="flex items-start gap-3 text-slate-300">
                  <Check className="mt-0.5 h-4 w-4 shrink-0 text-[#38bdf8]" />
                  <span>{r}</span>
                </li>
              ))}
            </ul>

            <Card className="mx-auto mt-10 max-w-xl border-white/10 bg-white/[0.04]">
              <CardContent className="p-6 text-center">
                <p className="text-slate-300">
                  ¿Necesitas cargar sobre Comandas Pro?{' '}
                  <a
                    href="https://comandas-opq6.onrender.com"
                    target="_blank"
                    rel="noreferrer noopener"
                    className="inline-flex items-center gap-1 font-semibold text-[#7dd3fc] hover:underline"
                  >
                    Abre Comandas Pro
                    <ExternalLink className="h-3.5 w-3.5" />
                  </a>
                </p>
              </CardContent>
            </Card>
          </div>
        </section>
      </main>

      <footer className="border-t border-white/10 px-6 py-6 text-center text-sm text-slate-500">
        © 2026 PreCarga · PreCarga Bot {VERSION.numero} · Desarrollado por{' '}
        <span className="text-[#7dd3fc]">Angel Valenzuela</span>
      </footer>
    </div>
  )
}