import { useOpeningStatus } from '../hooks/useOpeningStatus'

// Renders nothing for permanently closed points (that's handled separately via
// greyed-out styling) or when opening_hours is missing/unparseable.
export default function OpenStatusBadge({ openingHours, region }) {
  const status = useOpeningStatus(openingHours, region)
  if (!status || status.permanentlyClosed) return null

  if (status.temporarilyClosed) {
    return (
      <span className="inline-flex items-center gap-1.5 text-xs font-medium text-amber-600">
        <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
        Cerrado temporalmente
      </span>
    )
  }

  return (
    <span
      className={`inline-flex items-center gap-1.5 text-xs font-medium ${status.isOpen ? 'text-green-600' : 'text-gray-400'}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${status.isOpen ? 'bg-green-500' : 'bg-gray-400'}`} />
      {status.isOpen ? 'Abierto ahora' : 'Cerrado ahora'}
    </span>
  )
}
