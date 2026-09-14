export default function FilterChips({ donationType, onSelectDonationType, counts, showOnlyFixed, onToggleFixed }) {
  return (
    <div className="flex flex-wrap items-center justify-center md:justify-end gap-2">
      <Chip
        label={`Sangre (${counts.sangre})`}
        checked={donationType === 'sangre'}
        onClick={() => onSelectDonationType('sangre')}
      />
      <Chip
        label={`Médula (${counts.medula})`}
        checked={donationType === 'medula'}
        onClick={() => onSelectDonationType('medula')}
      />
      <Chip
        label={`Plasma (${counts.plasma})`}
        checked={donationType === 'plasma'}
        onClick={() => onSelectDonationType('plasma')}
      />
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
