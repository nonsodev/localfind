import { useEffect, useState } from 'react'
import ModernHome from './pages/ModernHome'

const VALID_ROUTES = new Set(['/search', '/agent', '/folders', '/analytics'])

function getCurrentRoute() {
  const path = window.location.pathname
  return VALID_ROUTES.has(path) ? path : '/search'
}

export default function App() {
  const [route, setRoute] = useState(getCurrentRoute)

  useEffect(() => {
    if (!VALID_ROUTES.has(window.location.pathname)) {
      window.history.replaceState({}, '', '/search')
    }

    const handlePopState = () => {
      setRoute(getCurrentRoute())
    }

    window.addEventListener('popstate', handlePopState)
    return () => window.removeEventListener('popstate', handlePopState)
  }, [])

  const navigate = (nextRoute) => {
    if (nextRoute === route) return
    window.history.pushState({}, '', nextRoute)
    setRoute(nextRoute)
  }

  return <ModernHome route={route} navigate={navigate} />
}
