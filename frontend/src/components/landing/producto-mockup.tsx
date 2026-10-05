import { cn } from '@/lib/utils'

/* ============================================================
   Mockups de pantalla del carrusel del hero.

   Son SVG y no <img>: pesan 0, se ven nitidos en cualquier DPI y toman los
   colores del tema, asi que no hay que regenerarlos cuando cambie el modo.

   MockPrecarga replica la captura real del dashboard (sidebar + topbar con
   Ctrl+K, 5 tarjetas de totales, selector de periodo, las dos barras de
   Programacion y el Altas vs Bajas con sus 4 series).

   Para usar capturas reales en vez de estos vectores: reemplazar el <svg>
   dentro de MockupEnMarco por
     <img src="/mockups/precarga.png" alt="..." className="block w-full" />
   y dejar intacto el contenedor (marco, sombra y reflejo).
   ============================================================ */

const C = {
  barra: '#15151a',
  barraActiva: 'rgba(0,120,212,0.20)',
  marco: '#2f2f38',
  panel: '#212126',
  panelAlto: '#26262c',
  borde: '#33333a',
  bordeSuave: '#2b2b32',
  texto: '#c9c9d1',
  textoTenue: '#8a8a95',
  textoFaint: '#5e5e69',
  primario: '#0078d4',
  violeta: '#a78bfa',
  violetaHondo: '#8b5cf6',
  cielo: '#38bdf8',
  cieloHondo: '#0284c7',
  esmeralda: '#34d399',
  naranja: '#fb923c',
  teal: '#2dd4bf',
}

const FUENTE = 'Segoe UI, Inter, system-ui, sans-serif'

/* Helpers de dibujo: repetirlos a mano hacia el archivo ilegible. */
function T({
  x,
  y,
  n,
  size = 7,
  fill = C.texto,
  weight = 500,
  anchor = 'start',
  o = 1,
}: {
  x: number
  y: number
  n: string | number
  size?: number
  fill?: string
  weight?: number
  anchor?: 'start' | 'middle' | 'end'
  o?: number
}) {
  return (
    <text
      x={x}
      y={y}
      fill={fill}
      fontSize={size}
      fontWeight={weight}
      textAnchor={anchor}
      fontFamily={FUENTE}
      opacity={o}
    >
      {n}
    </text>
  )
}

function R({
  x,
  y,
  w,
  h,
  fill = C.panel,
  stroke = C.borde,
  rx = 6,
  o = 1,
}: {
  x: number
  y: number
  w: number
  h: number
  fill?: string
  stroke?: string
  rx?: number
  o?: number
}) {
  return (
    <rect
      x={x}
      y={y}
      width={w}
      height={h}
      fill={fill}
      stroke={stroke}
      rx={rx}
      opacity={o}
    />
  )
}

/* Barras con remate redondeado solo arriba: es la forma que usa Recharts,
   y un <rect rx> las deja con las cuatro esquinas redondeadas. */
function Barra({
  x,
  y,
  w,
  h,
  fill,
  o = 1,
}: {
  x: number
  y: number
  w: number
  h: number
  fill: string
  o?: number
}) {
  const r = Math.min(1.6, w / 2, h / 2)
  return (
    <path
      d={`M${x},${y + h} L${x},${y + r} Q${x},${y} ${x + r},${y} L${x + w - r},${y} Q${x + w},${y} ${x + w},${y + r} L${x + w},${y + h} Z`}
      fill={fill}
      opacity={o}
    />
  )
}

/* ---------------- Marco ---------------- */

const CLASE_MARCO = 'block h-auto w-full'

function Marco({
  children,
  etiqueta,
  className = CLASE_MARCO,
}: {
  children: React.ReactNode
  etiqueta: string
  className?: string
}) {
  return (
    <svg
      viewBox="0 0 700 440"
      className={className}
      role="img"
      aria-label={etiqueta}
      fontFamily={FUENTE}
    >
      <rect width="700" height="440" fill={C.barra} />
      <rect x="0.5" y="0.5" width="699" height="439" rx="8" fill="none" stroke={C.marco} />
      {children}
    </svg>
  )
}

/* ---------------- 1. PreCarga: el dashboard real ---------------- */

const RANGOS = ['06/09', '08/09', '09/09', '10/09', '12/09', '14/09', '16/09', '18/09', '20/09', '22/09', '24/09', '26/09', '28/09', '30/09', '02/10', '05/10']

function MockPrecarga() {
  // Alturas de barra tomadas de la captura real, normalizadas a 0-1.
  const rpx = [1, 0.05, 0.21, 0.14, 0.22, 0, 0.5, 0.1, 0.09, 0.02, 0.65, 0.04, 0, 0, 0.33, 0.1, 0.88, 0]
  const cpz = [0.08, 0.12, 0.09, 0.17, 0.27, 0.03, 0.6, 0.02, 0.06, 0, 0.04, 0.02, 0, 0, 0.75, 0.04, 0.82, 0.02]

  // Las cuatro series del Altas vs Bajas. Mismo criterio que AREA_SERIES en
  // dashboard.tsx: violeta = RPX, cielo = CPZ, tonalidad clara = altas.
  const sRpxAltas = [200, 30, 8, 6, 4, 3, 2, 2, 3, 4, 3, 5, 8, 14, 20, 26, 34, 30, 26, 120, 150, 160, 26, 40, 120, 140, 20, 26, 10, 6, 4, 60, 130, 200, 180, 150]
  const sRpxBajas = [200, 34, 12, 9, 6, 5, 4, 3, 4, 6, 5, 8, 12, 18, 24, 30, 40, 34, 30, 128, 158, 168, 30, 46, 128, 148, 24, 30, 12, 8, 6, 66, 138, 208, 186, 156]
  const sCpzAltas = [200, 20, 6, 5, 3, 2, 2, 2, 2, 3, 3, 4, 5, 8, 10, 12, 16, 14, 12, 18, 22, 24, 10, 14, 26, 30, 8, 10, 5, 4, 3, 22, 60, 70, 62, 56]
  const sCpzBajas = [200, 24, 9, 7, 5, 4, 3, 3, 3, 4, 4, 6, 8, 12, 15, 18, 22, 20, 17, 24, 28, 30, 14, 19, 34, 38, 12, 14, 7, 6, 5, 28, 70, 80, 72, 66]

  // Panel del grafico de areas: x 196..690, baseline y=412, tope 220 -> y=348
  const AX = 196
  const AW = 690 - AX
  const AY = 412
  const AH = 412 - 348
  const curva = (ys: number[]) =>
    ys.map((v, i) => `${AX + (i * AW) / (ys.length - 1)},${AY - (v / 220) * AH}`).join(' ')
  const relleno = (ys: number[]) =>
    `M${AX},${AY} L${curva(ys)} L${AX + AW},${AY} Z`

  const tarjeta = (
    x: number,
    titulo: string,
    valor: string,
    pista: string,
    color: string,
  ) => (
    <g key={titulo}>
      <R x={x} y={74} w={98} h={52} rx={6} />
      <T x={x + 9} y={88} n={titulo} size={6.5} fill={C.texto} weight={600} />
      <T x={x + 9} y={107} n={valor} size={13} fill="#ffffff" weight={700} />
      <T x={x + 9} y={118} n={pista} size={5.5} fill={C.textoFaint} />
      <circle cx={x + 86} cy={84} r={0} fill="none" />
      <rect x={x + 83} y={81} width={7} height={7} rx={1.6} fill={color} opacity={0.95} />
    </g>
  )

  const graficoBarras = (
    x: number,
    titulo: string,
    total: number,
    color: string,
    datos: number[],
  ) => (
    <g key={titulo}>
      <R x={x} y={166} w={256} h={134} rx={7} />
      <T x={x + 11} y={182} n={titulo} size={7} fill={C.texto} weight={600} />
      <T x={x + 245} y={182} n={total} size={8} fill={color} weight={700} anchor="end" />

      {/* eje Y */}
      {[220, 165, 110, 55, 0].map((v, i) => {
        const y = 190 + (i * AH) / 4
        return (
          <g key={v}>
            <line
              x1={x + 26}
              y1={y}
              x2={x + 247}
              y2={y}
              stroke="#ffffff"
              strokeOpacity={v === 0 ? 0.14 : 0.055}
              strokeDasharray={v === 0 ? undefined : '2 3'}
            />
            <T x={x + 21} y={y + 2.4} n={v} size={5} fill={C.textoFaint} anchor="end" />
          </g>
        )
      })}

      {/* barras */}
      {datos.map((v, i) => {
        const paso = (247 - 30) / datos.length
        const bx = x + 29 + i * paso + (paso - 3.4) / 2
        const bh = v * AH
        if (bh < 0.4) return null
        return (
          <Barra
            key={i}
            x={bx}
            y={190 + AH - bh}
            w={3.4}
            h={bh}
            fill={color}
            o={0.92}
          />
        )
      })}

      {/* eje X */}
      {RANGOS.map((r, i) => {
        const paso = (247 - 30) / RANGOS.length
        return (
          <T
            key={r}
            x={x + 30 + i * paso + paso / 2}
            y={190 + AH + 9}
            n={r}
            size={4.6}
            fill={C.textoFaint}
            anchor="middle"
          />
        )
      })}
    </g>
  )

  return (
    <Marco etiqueta="Captura del dashboard de PreCarga: menú lateral, barra de búsqueda con Ctrl+K, cinco tarjetas de totales, selector de periodo, gráficas de programación RPX y CPZ, y la gráfica de Altas contra Bajas con cuatro series.">
      {/* ---- barra lateral ---- */}
      <rect x="0" y="0" width="150" height="440" fill={C.barra} />
      <line x1="150" y1="0" x2="150" y2="440" stroke={C.bordeSuave} />

      {/* logo real del sidebar, no un cuadrado azul dibujado a mano */}
      <image
        href="/logos/precarga-icono.svg"
        x="15"
        y="15.5"
        width="20"
        height="14.5"
        preserveAspectRatio="xMidYMid meet"
      />
      <T x={41} y={22} n="PreCarga" size={8} fill="#ffffff" weight={700} />
      <T x={41} y={30} n="Operaciones Marinas" size={5} fill={C.textoFaint} />

      <line x1="10" y1={44} x2="140" y2={44} stroke={C.bordeSuave} />

      {[
        ['Dashboard', 54, true],
        ['Procesar PDF', 72, false],
        ['Altas', 90, false],
        ['Bajas', 108, false],
        ['Compañías', 126, false],
        ['Activos', 144, false],
        ['Logs', 162, false],
        ['Novedades', 180, false],
      ].map(([n, y, activo]) => (
        <g key={String(n)}>
          {activo && <R x={8} y={Number(y) - 9} w={134} h={18} rx={5} fill={C.barraActiva} stroke="none" />}
          <rect x={14} y={Number(y) - 5} width={6} height={6} rx={1.5} fill={activo ? C.primario : C.textoFaint} />
          <T x={27} y={Number(y) + 1} n={String(n)} size={6.5} fill={activo ? '#ffffff' : C.textoTenue} weight={activo ? 600 : 500} />
        </g>
      ))}

      <line x1="10" y1={198} x2="140" y2="198" stroke={C.bordeSuave} />
      <T x={14} y={212} n="ADMINISTRACIÓN" size={4.8} fill={C.textoFaint} weight={700} />
      <rect x={14} y={220} width={6} height={6} rx={1.5} fill={C.textoFaint} />
      <T x={27} y={226} n="Usuarios" size={6.5} fill={C.textoTenue} />

      {/* cerrar sesion */}
      <line x1="10" y1={400} x2="140" y2="400" stroke={C.bordeSuave} />
      <rect x={14} y={412} width={6} height={6} rx={1.5} fill={C.textoFaint} />
      <T x={27} y={418} n="Cerrar Sesión" size={6.5} fill={C.textoTenue} />

      {/* ---- barra superior ---- */}
      <rect x="150" y="0" width="550" height="38" fill={C.panelAlto} opacity={0.5} />
      <line x1="150" y1="38" x2="700" y2="38" stroke={C.bordeSuave} />

      {/* menu hamburguesa */}
      {[0, 1, 2].map((i) => (
        <rect key={i} x={166} y={15 + i * 3} width={9} height={1.2} rx={0.6} fill={C.textoTenue} />
      ))}

      {/* buscador */}
      <R x={186} y={11} w={196} h={16} rx={8} fill={C.barra} stroke={C.bordeSuave} />
      <circle cx={196} cy={18} r={3} fill="none" stroke={C.textoFaint} strokeWidth={0.9} />
      <line x1={198.4} y1={20.4} x2={200.4} y2={22.4} stroke={C.textoFaint} strokeWidth={0.9} />
      <T x={205} y={21} n="Buscar solicitudes, activos..." size={6} fill={C.textoFaint} />
      <R x={350} y={14} w={24} h={10} rx={3} fill={C.panelAlto} stroke={C.bordeSuave} />
      <T x={362} y={21} n="Ctrl K" size={4.8} fill={C.textoTenue} anchor="middle" />

      {/* campana + avatar */}
      <circle cx={648} cy={19} r={5} fill="none" stroke={C.textoTenue} strokeWidth={1} />
      <path d="M645.4,20.6a2.6,2.6,0,0,1,5.2,0" stroke={C.textoTenue} strokeWidth={1} fill="none" />
      <circle cx={678} cy={19} r={9} fill={C.primario} />
      <T x={678} y={22} n="A" size={7} fill="#ffffff" weight={700} anchor="middle" />

      {/* ---- contenido ---- */}
      <T x={164} y={62} n="Dashboard" size={13} fill="#ffffff" weight={700} />

      {tarjeta(164, 'Total Solicitudes', '653', 'folios registrados', C.primario)}
      {tarjeta(270, 'Total Movimientos', '9,035', 'altas + bajas', C.violeta)}
      {tarjeta(376, 'Altas Generadas', '5,315', 'personas que suben', C.esmeralda)}
      {tarjeta(482, 'Bajas Procesadas', '3,720', 'personas que bajan', C.naranja)}
      {tarjeta(588, 'Compañías', '35', 'razones sociales', C.teal)}

      {/* selector de periodo */}
      {[
        ['14 días', 44, false],
        ['1 mes', 38, true],
        ['6 meses', 46, false],
        ['1 año', 38, false],
      ].map(([n, w, activo], i) => {
        const x = 164 + [0, 48, 90, 140][i]
        return (
          <g key={String(n)}>
            <R
              x={x}
              y={136}
              w={Number(w)}
              h={18}
              rx={4}
              fill={activo ? C.primario : C.barra}
              stroke={activo ? C.primario : C.bordeSuave}
            />
            <T
              x={x + Number(w) / 2}
              y={148}
              n={String(n)}
              size={6}
              fill={activo ? '#ffffff' : C.textoTenue}
              weight={activo ? 600 : 500}
              anchor="middle"
            />
          </g>
        )
      })}

      {graficoBarras(164, 'Programación RPX · últimos 30 días', 934, C.violeta, rpx)}
      {graficoBarras(430, 'Programación CPZ · últimos 30 días', 133, C.cielo, cpz)}

      {/* ---- Altas vs Bajas ---- */}
      <R x={164} y={310} w={522} h={120} rx={7} />

      {/* casillas de serie */}
      {[
        ['RPX Altas', C.violeta],
        ['RPX Bajas', C.violetaHondo],
        ['CPZ Altas', C.cielo],
        ['CPZ Bajas', C.cieloHondo],
      ].map(([n, color], i) => {
        const x = 178 + i * 66
        return (
          <g key={String(n)}>
            <R x={x} y={320} w={60} h={13} rx={3.5} fill={`${color}22`} stroke={`${color}55`} />
            <path
              d={`M${x + 5},${326.5} l2.2,2.2 l4,-4.4`}
              stroke={color}
              strokeWidth={1.3}
              fill="none"
              strokeLinecap="round"
            />
            <T x={x + 14} y={329.5} n={String(n)} size={5.5} fill={color} weight={600} />
          </g>
        )
      })}

      {/* rejilla + areas */}
      {[220, 165, 110, 55].map((v, i) => {
        const y = 348 + (i * AH) / 4
        return (
          <g key={v}>
            <line x1={AX} y1={y} x2={690} y2={y} stroke="#ffffff" strokeOpacity={0.055} strokeDasharray="2 3" />
            <T x={AX - 6} y={y + 2.4} n={v} size={5} fill={C.textoFaint} anchor="end" />
          </g>
        )
      })}
      <line x1={AX} y1={AY} x2={690} y2={AY} stroke="#ffffff" strokeOpacity={0.14} />

      <path d={relleno(sCpzBajas)} fill={C.cieloHondo} opacity={0.16} />
      <path d={relleno(sCpzAltas)} fill={C.cielo} opacity={0.18} />
      <path d={relleno(sRpxBajas)} fill={C.violetaHondo} opacity={0.2} />
      <path d={relleno(sRpxAltas)} fill={C.violeta} opacity={0.26} />

      <polyline points={curva(sCpzBajas)} fill="none" stroke={C.cieloHondo} strokeWidth={1} strokeDasharray="2.5 2.5" />
      <polyline points={curva(sCpzAltas)} fill="none" stroke={C.cielo} strokeWidth={1.2} />
      <polyline points={curva(sRpxBajas)} fill="none" stroke={C.violetaHondo} strokeWidth={1} strokeDasharray="2.5 2.5" />
      <polyline points={curva(sRpxAltas)} fill="none" stroke={C.violeta} strokeWidth={1.4} />

      {/* eje X */}
      {['06/09', '07/09', '08/09', '09/09', '10/09', '11/09', '12/09', '13/09', '14/09', '15/09', '16/09', '17/09', '18/09', '19/09', '20/09', '21/09', '22/09', '23/09', '24/09', '25/09', '26/09', '27/09', '28/09', '29/09', '30/09', '01/10', '02/10', '03/10', '05/10'].map((r, i, arr) => (
        <T
          key={r}
          x={AX + (i * AW) / (arr.length - 1)}
          y={424}
          n={r}
          size={4.4}
          fill={C.textoFaint}
          anchor="middle"
        />
      ))}
    </Marco>
  )
}

/* ---------------- 2. PreCarga Bot: escena de la app ----------------
 *
 * Ilustracion de la aplicacion: el robot leyendo las comandas de desayuno,
 * comida y cena mientras la pantalla de Comandas procesa y asigna raciones
 * a las plataformas.
 *
 * A diferencia del resto, aqui los textos de la imagen SI son legibles y
 * reales (Comanda Desayuno #0412, Raciones 1,436, Cargando comandas 68%),
 * asi que la imagen hace de prueba de que la app existe y funciona.
 *
 * El archivo es /public/precarga-bot-comandas.webp (WebP, ~78 KB) a partir
 * del PNG original de 683 KB. No lleva marco de navegador encima porque la
 * ilustracion ya trae su propia ventana; un chrome seria ventana sobre
 * ventana.
 * ------------------------------------------------------------------ */

function MockBot() {
  return (
    <img
      src="/precarga-bot-comandas.webp"
      alt="PreCarga Bot: un robot lee las comandas de desayuno, comida y cena mientras la pantalla de Comandas procesa y asigna raciones a las plataformas. Se ven 128 comandas hoy, 1,436 raciones en 3 turnos, 12 plataformas en operacion, 7 pendientes por validar y un avance del 68%."
      width={1536}
      height={1024}
      decoding="async"
      className="block h-auto w-full"
    />
  )
}

/* ---------------- 3. Comandas Pro: captura real del sitio ----------------
 *
 * A diferencia de PreCarga y PreCarga Bot, aqui se usa una captura real de
 * Comandas Pro en vez de un SVG. Motivo: los seis indicadores (38 comandas,
 * 261 PAX, 149 morteras, 112 viandas...) y el desglose por compania son datos
 * reales de la operacion, y un dibujo los haria ver como maqueta inventada.
 *
 * El archivo es /public/comandas-pro.webp (WebP, ~39 KB). Conviene WebP y no
 * el PNG original de 270 KB: la captura es casi toda degradado oscuro y el
 * PNG comprime mal ese tipo de imagen.
 * ------------------------------------------------------------------ */

function MockComandas() {
  return (
    /* La captura sola mide 2.11:1, muy apaisada: a lone en la columna queda
       baja y desligada del texto de al lado. El marco de navegador le suma
       la barra superior y, de paso, la deja visualmente igual que las otras
       dos capturas del carrusel. */
    <div className="w-full">
      <div className="flex items-center gap-2 border-b border-white/[0.07] bg-[#2d2d33] px-3 py-2">
        <span className="h-2.5 w-2.5 rounded-full bg-[#ff5f57]" />
        <span className="h-2.5 w-2.5 rounded-full bg-[#febc2e]" />
        <span className="h-2.5 w-2.5 rounded-full bg-[#28c840]" />
        <span className="ml-2 flex h-5 flex-1 items-center rounded-full bg-[#15151a] px-3 text-[10px] text-[#5e5e69]">
          comandas-opq6.onrender.com
        </span>
      </div>

      {/* SIN loading="lazy" a proposito: el carrusel remonta el slide cada 7s
          con key={indice}, asi que el observador de lazy se reinscribe antes
          de que la carga termine y la imagen se queda en blanco de forma
          intermitente. Con 39 KB de WebP no compensa arriesgarse. */}
      <img
        src="/comandas-pro.webp"
        alt="Dashboard de Comandas Pro: seis indicadores —38 comandas, 261 PAX total, 261 de menú 1, 0 de menú 2, 149 morteras y 112 viandas—, el desglose de PAX por destino y por compañía, la distribución por transporte y la torta de asignación por área."
        width={1782}
        height={845}
        decoding="async"
        className="block h-auto w-full"
      />
    </div>
  )
}

const MOCKUPS = {
  precarga: MockPrecarga,
  bot: MockBot,
  comandas: MockComandas,
} as const

export type ClaveProducto = keyof typeof MOCKUPS

export function ProductoMockup({ clave }: { clave: ClaveProducto }) {
  const Mock = MOCKUPS[clave]
  return <Mock />
}

/* ============================================================
   Contenedor exterior: hace que el mockup parezca una captura flotando,
   con el resplandor azul del diseno de referencia y un reflejo de vidrio.
   ============================================================ */
export function MockupEnMarco({
  clave,
  className,
}: {
  clave: ClaveProducto
  className?: string
}) {
  return (
    <div
      className={cn(
        'relative overflow-hidden rounded-xl',
        // El borde azul + el resplandor son lo que hace legible la captura
        // sobre el fondo oscuro; sin el parece un rectangulo plano pegado.
        'border border-primary/45 shadow-[0_0_0_1px_rgba(0,120,212,0.25),0_24px_70px_-14px_rgba(0,120,212,0.55)]',
        className,
      )}
    >
      <div className="pointer-events-none absolute inset-x-0 top-0 h-1/3 bg-gradient-to-b from-white/[0.05] to-transparent" />
      <div className="relative">
        <ProductoMockup clave={clave} />
      </div>
    </div>
  )
}