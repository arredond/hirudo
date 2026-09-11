import { useState } from 'react'
import dayjs from 'dayjs'
import 'dayjs/locale/es'
import Header from './components/Header'
import DateNav from './components/DateNav'
import MapView from './components/MapView'
import ListPanel from './components/ListPanel'
import Popup from './components/Popup'
import { useBloodPoints } from './hooks/useBloodPoints'
import { useNowTick } from './hooks/useNowTick'
import { getOpenStatus } from './lib/openingHours'

dayjs.locale('es')

export default function App() {
  const [selectedDate, setSelectedDate] = useState(dayjs())
  const [selectedPoint, setSelectedPoint] = useState(null)
  const [showList, setShowList] = useState(false)
  const [showOnlyFixed, setShowOnlyFixed] = useState(false)
  const [userLocation, setUserLocation] = useState(null)
  const [mapCenter, setMapCenter] = useState({ lat: 40.4, lng: -3.7 })

  const { fixedPoints, mobilePoints, loadingMobile } = useBloodPoints(selectedDate)
  const now = useNowTick()

  // The "Abierto ahora" tab selects selectedDate = null (see DateNav) — when
  // active, only show points that are actually open right now.
  const showOnlyOpenNow = selectedDate === null
  const filterByOpenNow = features =>
    showOnlyOpenNow
      ? features.filter(f => getOpenStatus(f.properties?.opening_hours, now)?.isOpen === true)
      : features

  const visibleFixedPoints = filterByOpenNow(fixedPoints)
  const visibleMobilePoints = filterByOpenNow(showOnlyFixed ? [] : mobilePoints)


  return (
    <div className="flex flex-col h-screen bg-white">
      <Header />
      <DateNav
        selectedDate={selectedDate}
        onSelectDate={setSelectedDate}
        showOnlyFixed={showOnlyFixed}
        onToggleFixed={() => setShowOnlyFixed(v => !v)}
      />
      <div className="flex flex-1 overflow-hidden">
        {showList && (
          <ListPanel
            fixedPoints={visibleFixedPoints}
            mobilePoints={visibleMobilePoints}
            selectedPoint={selectedPoint}
            onSelectPoint={setSelectedPoint}
            onClose={() => setShowList(false)}
            refPoint={userLocation ?? mapCenter}
            locationGranted={userLocation !== null}
          />
        )}
        <div className="flex-1 relative">
          <MapView
            fixedPoints={visibleFixedPoints}
            mobilePoints={visibleMobilePoints}
            selectedPoint={selectedPoint}
            onSelectPoint={setSelectedPoint}
            onUserLocation={setUserLocation}
            onCenterChange={setMapCenter}
          />
          {!showList && (
            <button
              onClick={() => setShowList(true)}
              className="absolute top-4 left-4 z-10 bg-white rounded-full px-4 py-2 shadow-md text-sm font-medium flex items-center gap-2 hover:bg-gray-50 transition-colors"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="3" y1="6" x2="21" y2="6" />
                <line x1="3" y1="12" x2="21" y2="12" />
                <line x1="3" y1="18" x2="21" y2="18" />
              </svg>
              Mostrar lista
            </button>
          )}
          {selectedPoint && (
            <Popup point={selectedPoint} onClose={() => setSelectedPoint(null)} />
          )}
        </div>
      </div>
    </div>
  )
}
