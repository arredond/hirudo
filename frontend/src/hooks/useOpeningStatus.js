import { getOpenStatus } from '../lib/openingHours'
import { useNowTick } from './useNowTick'

export function useOpeningStatus(openingHoursString, region) {
  const now = useNowTick()
  return getOpenStatus(openingHoursString, now, region)
}
