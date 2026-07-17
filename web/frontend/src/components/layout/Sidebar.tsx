import { Clock, Eye, Home, Settings } from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { cn } from '@/lib/utils'

const navItems = [
  { to: '/', label: 'Dashboard', icon: Home },
  { to: '/history', label: 'History', icon: Clock },
  { to: '/watchlists', label: 'Watchlists', icon: Eye },
  { to: '/settings', label: 'Settings', icon: Settings },
] as const

export function Sidebar() {
  return (
    <aside className="hidden w-64 flex-shrink-0 flex-col border-r bg-background md:flex">
      <div className="flex h-14 items-center border-b px-6">
        <span className="text-base font-semibold tracking-tight">AMCTracker</span>
      </div>
      <nav className="flex flex-1 flex-col gap-1 p-3">
        {navItems.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-accent text-accent-foreground'
                  : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
              )
            }
          >
            <Icon className="h-4 w-4 flex-shrink-0" />
            {label}
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}
