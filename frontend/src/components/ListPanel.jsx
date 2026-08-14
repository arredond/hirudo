import { useState, useEffect, useRef } from 'react'
import PointCard from './PointCard'

function haversine(lat1, lng1, lat2, lng2) {
  const R = 6371
  const toRad = x => (x * Math.PI) / 180
  const dLat = toRad(lat2 - lat1)
  const dLng = toRad(lng2 - lng1)
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLng / 2) ** 2
  return R * 2 * Math.asin(Math.sqrt(a))
}

function LocationTooltip() {
  const [open, setOpen] = useState(false)
  return (
    <div className="relative">
      <button
        onClick={() => setOpen(v => !v)}
        className="flex items-center gap-1 text-xs text-amber-600 hover:text-amber-700 transition-colors"
        aria-label="Información sobre distancias"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
          <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z" />
        </svg>
        Distancia aproximada
      </button>
      {open && (
        <div className="absolute left-0 top-6 z-30 w-64 bg-gray-900 text-white text-xs rounded-xl p-3 shadow-xl leading-relaxed">
          Las distancias se calculan desde el centro del mapa. Para medidas más precisas, comparte tu ubicación cuando el navegador te lo solicite.
          <div className="absolute -top-1.5 left-3 w-3 h-3 bg-gray-900 rotate-45" />
        </div>
      )}
    </div>
  )
}

export default function ListPanel({ fixedPoints, mobilePoints, selectedPoint, onSelectPoint, onClose, refPoint, locationGranted }) {
  const scrollRef = useRef(null)
  const selectedRef = useRef(null)

  useEffect(() => {
    if (selectedRef.current && scrollRef.current) {
      selectedRef.current.scrollIntoView({ block: 'center', behavior: 'smooth' })
    }
  }, [selectedPoint])

  const all = [...mobilePoints, ...fixedPoints]

  const withDistance = all.map(point => {
    const [lng, lat] = point.geometry.coordinates
    const dist = refPoint ? haversine(refPoint.lat, refPoint.lng, lat, lng) : null
    return { point, dist }
  })

  if (refPoint) {
    withDistance.sort((a, b) => a.dist - b.dist)
  }

  return (
    <div className="fixed inset-0 z-40 md:relative md:inset-auto md:z-auto md:w-[560px] md:shrink-0 flex flex-col border-r border-gray-200 bg-white overflow-hidden">
      <div className="flex items-center justify-between px-6 py-3 border-b border-gray-100">
        <div className="flex items-center gap-3">
          <span className="text-sm font-medium text-gray-700">
            {withDistance.length} {withDistance.length === 1 ? 'punto' : 'puntos'}
          </span>
          {!locationGranted && <LocationTooltip />}
        </div>
        <button
          onClick={onClose}
          className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-800 transition-colors"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="15 18 9 12 15 6" />
          </svg>
          Ocultar lista
        </button>
      </div>
      <div ref={scrollRef} className="overflow-y-auto flex-1">
        {withDistance.length === 0 && (
          <p className="text-sm text-gray-400 text-center mt-12">No hay puntos para esta fecha.</p>
        )}
        {withDistance.map(({ point, dist }, i) => (
          <PointCard
            key={point.properties.nombre + i}
            point={point}
            isSelected={point === selectedPoint}
            distanceKm={dist}
            onClick={() => onSelectPoint(point)}
            itemRef={point === selectedPoint ? selectedRef : null}
          />
        ))}
      </div>
    </div>
  )
}
