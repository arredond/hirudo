import { useBloodLevels } from '../hooks/useBloodLevels'

const STATUS_COLOR = {
  urgent: 'bg-red-600',
  soon: 'bg-amber-500',
  stable: 'bg-green-600',
}

export default function BloodLevelBadges({ region }) {
  const { bloodLevels, hasLoaded } = useBloodLevels(region)

  // Still loading, or no region resolved yet — say nothing rather than
  // flash a "no data" message that a moment later turns out to be wrong.
  if (!hasLoaded) return null

  // Loaded, but genuinely nothing for this region (e.g. Castilla-La Mancha,
  // which has no blood-levels source at all — see REGION_CLM in etl/main.py).
  if (bloodLevels.length === 0) {
    return (
      <p className="max-w-[200px] shrink-0 text-right text-xs italic text-gray-500 sm:max-w-xs sm:text-sm">
        En este momento no disponemos de niveles de donación para {region}.
      </p>
    )
  }

  return (
    <div className="flex items-center gap-1 sm:gap-2 shrink-0">
      {bloodLevels.map(({ blood_type: bloodType, status, label }) => (
        <span
          key={bloodType}
          title={label ?? undefined}
          className={`w-5 h-5 sm:w-9 sm:h-9 rounded-full flex items-center justify-center text-white text-[7px] sm:text-xs font-semibold select-none leading-none ${STATUS_COLOR[status] ?? 'bg-gray-400'}`}
        >
          {bloodType}
        </span>
      ))}
    </div>
  )
}
