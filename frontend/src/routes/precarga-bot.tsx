import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { BrandLockup } from '@/components/brand'
import {
  Bot,
  Download,
  MonitorDown,
  RefreshCw,
  ShieldCheck,
  Zap,
  Check,
  ExternalLink,
  ArrowLeft,
} from 'lucide-react'

/* ============================================================
   Pagina de descarga de PreCarga Bot.

   Estatica a proposito: no pide sesion ni consulta la API, asi que se puede
   publicar como HTML plano si algun dia se quiere separar de este proyecto.

   PARA PUBLICAR UNA VERSION NUEVA: agregar el objeto al inicio de VERSIONES y
   subir el .exe a /public/descargas con el nombre de `archivo`. Nada mas.
   El `peso` se escribe a mano porque la pagina es estatica y no hay forma de
   saber el tamano del archivo sin pedirlo al servidor.
   ============================================================ */

interface Version {
  numero: string
  fecha: string
  archivo: string
  peso: string
  recomendada: boolean
  cambios: string[]
}

const VERSIONES: Version[] = [
  {
    numero: '1.4.2',
    fecha: '5 de octubre de 2026',
    archivo: '/descargas/PreCargaBot-1.4.2-setup.exe',
    peso: '18.4 MB',
    recomendada: true,
    cambios: [
      'Reintenta la carga de un registro si el sitio responde con error.',
      'Muestra el progreso por comanda y no solo el total.',
      'Permite pausar y reanudar la carga sin perder lo ya subido.',
    ],
  },
  {
    numero: '1.4.1',
    fecha: '28 de septiembre de 2026',
    archivo: '/descargas/PreCargaBot-1.4.1-setup.exe',
    peso: '18.2 MB',
    recomendada: false,
    cambios: [
      'Corrige el corte de línea con acentos en el destino.',
      'Guarda la configuración de la última carga usada.',
    ],
  },
  {
    numero: '1.4.0',
    fecha: '19 de septiembre de 2026',
    archivo: '/descargas/PreCargaBot-1.4.0-setup.exe',
    peso: '18.0 MB',
    recomendada: false,
    cambios: [
      'Bitácora de la carga con cada registro enviado.',
      'Detecta registros duplicados antes de subirlos.',
    ],
  },
  {
    numero: '1.3.6',
    fecha: '2 de septiembre de 2026',
    archivo: '/descargas/PreCargaBot-1.3.6-setup.exe',
    peso: '17.6 MB',
    recomendada: false,
    cambios: [
      'Primera versión pública.',
      'Carga automática de alimentos al área.',
    ],
  },
]

const REQUISITOS = [
  'Windows 10 o superior (64 bits).',
  'Conexión a internet durante la carga.',
  'Permiso de escritura en la carpeta que elijas para el archivo de registros.',
]

const PUNTOS = [
  {
    icono: Zap,
    titulo: 'Carga automática',
    detalle: 'Sube los alimentos al área sin capturarlos uno por uno.',
  },
  {
    icono: MonitorDown,
    titulo: 'Instalador .exe',
    detalle: 'Un solo archivo, doble clic y listo. Sin dependencias.',
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
  const recomendada = VERSIONES.find((v) => v.recomendada) ?? VERSIONES[0]

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
            <span className="inline-flex items-center gap-2 rounded-full border border-primary/40 bg-primary/10 px-4 py-1.5 text-[13px] font-medium text-white">
              <Bot className="h-4 w-4 text-[#38bdf8]" />
              Aplicación de escritorio para Windows
            </span>

            <h1 className="mt-6 text-4xl font-extrabold leading-[1.06] tracking-tight text-white sm:text-5xl">
              PreCarga Bot
              <span className="block bg-gradient-to-r from-[#7dd3fc] via-[#38bdf8] to-[#818cf8] bg-clip-text text-transparent">
                descarga la última versión
              </span>
            </h1>

            <p className="mx-auto mt-5 max-w-xl text-lg text-slate-300">
              Automatiza la carga de alimentos al área de tus barcos. Elige la
              versión que quieras y corre el instalador.
            </p>

            <div className="mt-9 flex flex-wrap items-center justify-center gap-3">
              <Button size="lg" className="gap-2 px-7" asChild>
                <a href={recomendada.archivo} download>
                  <Download className="h-4 w-4" />
                  Descargar {recomendada.numero}
                </a>
              </Button>
              <Button size="lg" variant="outline" className="px-7" asChild>
                <a href="#versiones">Ver todas las versiones</a>
              </Button>
            </div>

            <p className="mt-4 text-sm text-slate-400">
              Recomendada: {recomendada.numero} · {recomendada.peso} ·{' '}
              {recomendada.fecha}
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
                alt="PreCarga Bot procesando archivos: un robot analiza documentos de Excel y PDF mientras el dashboard muestra el avance de la carga al 68%."
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

        {/* ---------------- versiones ---------------- */}
        <section
          id="versiones"
          className="scroll-mt-20 border-t border-white/10 bg-white/[0.02] px-6 py-16"
        >
          <div className="mx-auto max-w-4xl">
            <h2 className="text-center text-2xl font-bold text-white sm:text-3xl">
              Versiones recientes
            </h2>
            <p className="mx-auto mt-2 max-w-lg text-center text-slate-400">
              Si algo falla al actualizar, usa una versión anterior: cada una
              queda disponible para descarga.
            </p>

            <div className="mt-10 grid gap-4">
              {VERSIONES.map((v) => (
                <Card
                  key={v.numero}
                  className={
                    v.recomendada
                      ? 'border-primary/50 bg-primary/[0.07]'
                      : 'border-white/10 bg-white/[0.04]'
                  }
                >
                  <CardContent className="p-5">
                    <div className="flex flex-wrap items-start justify-between gap-4">
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <h3 className="text-lg font-bold text-white">
                            Versión {v.numero}
                          </h3>
                          {v.recomendada && (
                            <span className="rounded-full bg-primary/20 px-2 py-0.5 text-[11px] font-semibold text-[#7dd3fc]">
                              Recomendada
                            </span>
                          )}
                        </div>
                        <p className="mt-0.5 text-sm text-slate-400">
                          {v.fecha} · {v.peso}
                        </p>
                      </div>

                      <Button
                        variant={v.recomendada ? 'accent' : 'outline'}
                        className="gap-2"
                        asChild
                      >
                        <a href={v.archivo} download>
                          <Download className="h-4 w-4" />
                          Descargar .exe
                        </a>
                      </Button>
                    </div>

                    <ul className="mt-4 grid gap-1.5">
                      {v.cambios.map((c) => (
                        <li key={c} className="flex items-start gap-2 text-sm text-slate-400">
                          <Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#38bdf8]" />
                          <span>{c}</span>
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        </section>

        {/* ---------------- requisitos ---------------- */}
        <section className="border-t border-white/10 px-6 py-16">
          <div className="mx-auto max-w-4xl">
            <h2 className="text-center text-2xl font-bold text-white sm:text-3xl">
              Requisitos
            </h2>
            <ul className="mx-auto mt-8 grid max-w-xl gap-3">
              {REQUISITOS.map((r) => (
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
        © 2026 PreCarga · PreCarga Bot v{recomendada.numero} · Desarrollado por{' '}
        <span className="text-[#7dd3fc]">Angel Valenzuela</span>
      </footer>
    </div>
  )
}