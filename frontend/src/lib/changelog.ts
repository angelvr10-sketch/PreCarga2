// Version y contenido de "Novedades". Igual que precarga usa core/config.py
// VERSION, aqui la version vive en el frontend porque la app no expone una
// ruta de version. Al hacer un release, incrementarla para que el modal
// vuelva a mostrarse una vez por usuario.
export const VERSION = '0.6'

export interface Cambio {
  icono: string
  titulo: string
  detalle: string
}

// Lo mas reciente debe ir primero.
export const CAMBIOS: Cambio[] = [
  {
    icono: '📈',
    titulo: 'Nueva interfaz de graficas',
    detalle:
      'El tablero se rediseño con graficas de comportamiento: selector de periodo (14 dias, 1 mes, 6 meses, 1 año), graficas de Programación RPX y CPZ en barras separadas, y Altas vs Bajas en areas con cuatro series (RPX/CPZ por altas y bajas). La leyenda se volvio interactiva: podés apagar series para compararlas de a una.',
  },
  {
    icono: '⛶',
    titulo: 'Graficas a pantalla completa',
    detalle:
      'Cada grafica tiene su boton de pantalla completa para ver el comportamiento sin las tarjetas alrededor. Ademas se Aggregaron los datos de personal para que las graficas ya no se recortaran a 1000 registros.',
  },
  {
    icono: '🚀',
    titulo: 'Rendimiento',
    detalle:
      'Conexion persistente (keep-alive) a Supabase y el personal de cada solicitud se inserta en lotes en vez de uno por uno. Guardar una solicitud paso de abrir una conexion TLS por persona a reutilizar la misma.',
  },
  {
    icono: '📅',
    titulo: 'Fechas de las plantillas',
    detalle:
      'En Entradas C18 y en el campo Fecha de Solicitud se usa la fecha de llegada real del personal, no la del dia en que se abre la plantilla. En Salidas C18 se usa TODAY().',
  },
]
