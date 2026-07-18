import { Outlet } from 'react-router-dom'
import { BottomNav } from './BottomNav'
import { Sidebar } from './Sidebar'

export function AppShell() {
  return (
    <div className="flex min-h-svh bg-background pt-safe">
      <Sidebar />
      <main className="flex min-w-0 flex-1 flex-col pb-nav-safe md:pb-0">
        <Outlet />
      </main>
      <BottomNav />
    </div>
  )
}
