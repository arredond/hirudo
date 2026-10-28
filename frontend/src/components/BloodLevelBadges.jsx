import { useBloodLevels } from '../hooks/useBloodLevels'

// status is the colour each region's own source shows (etl/utils/crawl/*.py
// BLOOD_LEVEL_STATUS / BLOOD_LEVEL_COLOURS), so every region keeps its own
// scale: three steps for Madrid and Castilla y León, four for Galicia. The
// urgent/soon/stable keys cover rows written before status became a colour.
const STATUS_COLOR = {
  red: 'bg-red-600 text-white',
  orange: 'bg-orange-500 text-white',
  yellow: 'bg-yellow-400 text-gray-900',
  green: 'bg-green-600 text-white',
  urgent: 'bg-red-600 text-white',
  soon: 'bg-orange-500 text-white',
  stable: 'bg-green-600 text-white',
}

// Every state below renders in the same fixed-height slot (badge height), so
// the header — and the map under it — doesn't jump while panning between
// regions: badges, "no data" note and the empty loading state all take the
// same vertical space.
const SLOT = 'h-8 sm:h-9 flex items-center justify-end shrink-0'

export default function BloodLevelBadges({ region }) {
  const { bloodLevels, hasLoaded } = useBloodLevels(region)

  // Still loading, or no region resolved yet — say nothing rather than
  // flash a "no data" message that a moment later turns out to be wrong.
  if (!hasLoaded) return <div className={SLOT} />

  // Loaded, but genuinely nothing for this region (e.g. Castilla-La Mancha,
  // which has no blood-levels source at all — see REGION_CLM in etl/main.py).
  // Clamped to two lines so it fits the slot.
  if (bloodLevels.length === 0) {
    const message = `En este momento no disponemos de niveles de donación para ${region}.`
    return (
      <div className={SLOT}>
        <p
          title={message}
          className="max-w-[200px] sm:max-w-xs text-right text-[11px] leading-4 sm:text-xs sm:leading-[18px] italic text-gray-500 line-clamp-2"
        >
          {message}
        </p>
      </div>
    )
  }

  return (
    <div className={`${SLOT} gap-1 sm:gap-2`}>
      {bloodLevels.map(({ blood_type: bloodType, status, label }) => (
        <span
          key={bloodType}
          title={label ?? undefined}
          className={`w-5 h-5 sm:w-9 sm:h-9 rounded-full flex items-center justify-center text-[7px] sm:text-xs font-semibold select-none leading-none ${STATUS_COLOR[status] ?? 'bg-gray-400 text-white'}`}
        >
          {bloodType}
        </span>
      ))}
    </div>
  )
}
