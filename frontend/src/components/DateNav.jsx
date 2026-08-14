import dayjs from 'dayjs'

export default function DateNav({ selectedDate, onSelectDate, showOnlyFixed, onToggleFixed }) {
  const today = dayjs()
  const days = Array.from({ length: 5 }, (_, i) => today.add(i, 'day'))

  function label(i) {
    if (i === 0) return 'Hoy'
    if (i === 1) return 'Mañana'
    const name = days[i].format('dddd')
    return name.charAt(0).toUpperCase() + name.slice(1)
  }

  const isAbiertoAhora = selectedDate === null
  const isActive = day => selectedDate && day.isSame(selectedDate, 'day')

  return (
    <nav className="flex flex-col md:flex-row md:items-end md:justify-between border-b border-gray-200 shrink-0">
      <div className="flex items-end gap-4 md:gap-6 px-4 md:px-8 overflow-x-auto shrink-0">
        <Tab top="Abierto" bottom="ahora" active={isAbiertoAhora} onClick={() => onSelectDate(null)} />
        {days.map((day, i) => (
          <Tab
            key={day.format('YYYY-MM-DD')}
            top={label(i)}
            bottom={day.format('D MMM').toUpperCase()}
            active={isActive(day)}
            onClick={() => onSelectDate(day)}
          />
        ))}
      </div>

      <div className="px-4 md:px-8 py-2 md:pb-3 flex justify-end border-t border-gray-100 md:border-t-0">
        <button
          onClick={onToggleFixed}
          className={`flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-full border transition-colors ${
            showOnlyFixed
              ? 'bg-gray-900 text-white border-gray-900'
              : 'bg-white text-gray-600 border-gray-300 hover:border-gray-500'
          }`}
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor">
            <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-7 3c.55 0 1 .45 1 1v2h2c.55 0 1 .45 1 1v2c0 .55-.45 1-1 1h-2v2c0 .55-.45 1-1 1s-1-.45-1-1v-2H9c-.55 0-1-.45-1-1V9c0-.55.45-1 1-1h2V7c0-.55.45-1 1-1z" />
          </svg>
          Solo puntos fijos
        </button>
      </div>
    </nav>
  )
}

function Tab({ top, bottom, active, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`flex flex-col items-center py-3 border-b-2 -mb-px transition-colors shrink-0 ${
        active
          ? 'border-red-600 text-red-600'
          : 'border-transparent text-gray-500 hover:text-gray-800'
      }`}
    >
      <span className="text-sm font-semibold whitespace-nowrap">{top}</span>
      <span className="text-xs mt-0.5 whitespace-nowrap">{bottom}</span>
    </button>
  )
}
