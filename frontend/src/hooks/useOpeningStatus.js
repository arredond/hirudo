import { getOpenStatus } from '../lib/openingHours'
import { useNowTick } from './useNowTick'

export function useOpeningStatus(openingHoursString) {
  const now = useNowTick()
  return getOpenStatus(openingHoursString, now)
}
