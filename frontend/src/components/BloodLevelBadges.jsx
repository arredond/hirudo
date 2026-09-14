import { useBloodLevels } from '../hooks/useBloodLevels'

const STATUS_COLOR = {
  urgent: 'bg-red-600',
  soon: 'bg-amber-500',
  stable: 'bg-green-600',
}

// donarsangre.org spells "O" as digit "0" (see useBloodLevels) — displayed as the
// letter here, matching how blood types are normally written.
const displayType = bloodType => bloodType.replace('0', 'O')

export default function BloodLevelBadges() {
  const bloodLevels = useBloodLevels()
  if (bloodLevels.length === 0) return null

  return (
    <div className="flex items-center gap-1 sm:gap-2 shrink-0">
      {bloodLevels.map(({ blood_type: bloodType, status, label }) => (
        <span
          key={bloodType}
          title={label ?? undefined}
          className={`w-5 h-5 sm:w-9 sm:h-9 rounded-full flex items-center justify-center text-white text-[7px] sm:text-xs font-semibold select-none leading-none ${STATUS_COLOR[status] ?? 'bg-gray-400'}`}
        >
          {displayType(bloodType)}
        </span>
      ))}
    </div>
  )
}
