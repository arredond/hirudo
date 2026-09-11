import { useEffect, useState } from 'react'

const DEFAULT_INTERVAL_MS = 60_000

// Shared clock tick so open/closed status (badges, "Abierto ahora" filtering)
// refreshes periodically without each consumer running its own interval.
export function useNowTick(intervalMs = DEFAULT_INTERVAL_MS) {
  const [now, setNow] = useState(() => new Date())

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), intervalMs)
    return () => clearInterval(id)
  }, [intervalMs])

  return now
}
