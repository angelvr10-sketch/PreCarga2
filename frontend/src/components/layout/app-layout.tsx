import { Outlet } from '@tanstack/react-router'
import { Sidebar } from './sidebar'
import { Topbar } from './topbar'
import { ErrorBoundary } from '@/components/error-boundary'
import { ChangelogModal } from './changelog-modal'

export function AppLayout() {
  return (
    <ErrorBoundary>
      <div className="flex min-h-screen w-full">
        <Sidebar />
        <div className="flex min-w-0 flex-1 flex-col">
          <Topbar />
          <main className="flex-1 overflow-x-hidden px-6 py-8 md:px-10 fluent-scroll">
            {/*
              El ancho del area de contenido.

              Venia en `max-w-7xl` (1280px). En un monitor de 1920, con el
              sidebar de 256px, eso dejaba unos 380px vacios a cada lado: el
              contenido se veia pequeno y perdido en el centro de la pantalla.

              1760px aprovecha la pantalla sin que las tablas del listado se
              vuelvan-lines largas que obliguen a volver la vista al leer.

              Es el unico lugar donde se limita el ancho: los modales y los
              formularios cortos (`procesar`, `bajas`) traen su propio max-w y no
              se tocan, porque un formulario ancho se ve peor, no mejor.
            */}
            <div className="mx-auto w-full max-w-[1760px]">
              <Outlet />
            </div>
          </main>
        </div>
        {/* modal de novedades: se controla solo, se abre en /dashboard y desde
            el item "Novedades" del sidebar */}
        <ChangelogModal />
      </div>
    </ErrorBoundary>
  )
}
