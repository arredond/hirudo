export default function FilterChips({ donationTypes, onToggleDonationType, showOnlyFixed, onToggleFixed }) {
  return (
    <div className="flex flex-wrap items-center justify-end gap-2">
      <Chip label="Médula" checked={donationTypes.medula} onClick={() => onToggleDonationType('medula')} />
      <Chip label="Sangre" checked={donationTypes.sangre} onClick={() => onToggleDonationType('sangre')} />
      <Chip label="Plasma" checked={donationTypes.plasma} onClick={() => onToggleDonationType('plasma')} />
      <Chip label="Solo puntos fijos" checked={showOnlyFixed} onClick={onToggleFixed} />
    </div>
  )
}

function Chip({ label, checked, onClick }) {
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-1.5 text-sm text-gray-700 bg-white rounded-full shadow-md px-3.5 py-2 hover:bg-gray-50 transition-colors shrink-0"
    >
      <span
        className={`w-4 h-4 rounded-full border flex items-center justify-center transition-colors ${
          checked ? 'bg-red-600 border-red-600' : 'border-gray-300'
        }`}
      >
        {checked && (
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="20 6 9 17 4 12" />
          </svg>
        )}
      </span>
      {label}
    </button>
  )
}
