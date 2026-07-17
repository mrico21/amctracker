import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import { AppShell } from '@/components/layout/AppShell'
import Dashboard from '@/pages/Dashboard'
import History from '@/pages/History'
import RunDetails from '@/pages/RunDetails'
import Settings from '@/pages/Settings'
import Watchlists from '@/pages/Watchlists'

const router = createBrowserRouter([
  {
    path: '/',
    element: <AppShell />,
    children: [
      { index: true, element: <Dashboard /> },
      { path: 'history', element: <History /> },
      { path: 'history/:runId', element: <RunDetails /> },
      { path: 'watchlists', element: <Watchlists /> },
      { path: 'settings', element: <Settings /> },
    ],
  },
])

export default function App() {
  return <RouterProvider router={router} />
}
