import { useState, useRef, useEffect } from 'react'
import { REGIONS } from '../lib/regions'
import { DONATION_TYPES, DONATION_TYPE_LABELS } from '../lib/donationTypes'

function useOutsideClick(onOutside) {
  const ref = useRef(null)
  useEffect(() => {
    function handle(e) {
      if (ref.current && !ref.current.contains(e.target)) onOutside()
    }
    document.addEventListener('mousedown', handle)
    return () => document.removeEventListener('mousedown', handle)
  }, [onOutside])
  return ref
}

// One clickable red word in the title (donation type or region), opening a
// dropdown to override it manually — see TitleDropdown in HeaderTitle below.
function TitleDropdown({ label, value, options, renderOption, onSelect }) {
  const [open, setOpen] = useState(false)
  const ref = useOutsideClick(() => setOpen(false))

  return (
    <span ref={ref} className="relative inline-block">
      <button
        type="button"
        onClick={() => setOpen(v => !v)}
        className="text-red-600 underline decoration-2 decoration-red-200 underline-offset-4 hover:decoration-red-400 transition-colors"
      >
        {label}
      </button>
      {open && (
        <div className="absolute left-0 top-full mt-2 z-30 min-w-[11rem] bg-white text-gray-900 text-sm font-normal normal-case rounded-xl shadow-xl border border-gray-100 py-1 text-left">
          {options.map(option => (
            <button
              key={option}
              type="button"
              onClick={() => {
                onSelect(option)
                setOpen(false)
              }}
              className={`block w-full text-left px-3.5 py-2 hover:bg-gray-50 transition-colors ${
                option === value ? 'font-semibold' : ''
              }`}
            >
              {renderOption ? renderOption(option) : option}
            </button>
          ))}
        </div>
      )}
    </span>
  )
}

// "dónde donar [sangre] en [Castilla y León]" — the two bracketed words track
// the donation-type filter and the region the map is currently centered on
// (see nearestRegion in lib/regions.js), and are independently clickable to
// override either one directly from the title instead.
export default function HeaderTitle({ donationType, onSelectDonationType, region, onSelectRegion }) {
  return (
    <div className="text-base sm:text-2xl font-bold tracking-tight leading-tight min-w-0">
      <span className="text-black">dónde donar </span>
      <TitleDropdown
        label={DONATION_TYPE_LABELS[donationType] ?? donationType}
        value={donationType}
        options={DONATION_TYPES}
        renderOption={type => DONATION_TYPE_LABELS[type]}
        onSelect={onSelectDonationType}
      />
      <span className="text-black"> en </span>
      <TitleDropdown
        label={region ?? '…'}
        value={region}
        options={REGIONS}
        onSelect={onSelectRegion}
      />
    </div>
  )
}
