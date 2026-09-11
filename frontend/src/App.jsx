import { useState, useMemo, useRef, useLayoutEffect } from 'react'
import dayjs from 'dayjs'
import 'dayjs/locale/es'
import Header from './components/Header'
import DateNav from './components/DateNav'
import FilterChips from './components/FilterChips'
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
  const [donationTypes, setDonationTypes] = useState({ medula: false, sangre: true, plasma: true })
  const [userLocation, setUserLocation] = useState(null)
  const [mapCenter, setMapCenter] = useState({ lat: 40.4, lng: -3.7 })

  const { fixedPoints, mobilePoints, loadingMobile } = useBloodPoints(selectedDate)
  const now = useNowTick()

  // The list panel should match DateNav's own (content-driven) width — measured
  // rather than duplicated as a literal, since ListPanel's own content (long
  // addresses, buttons, ...) is wide enough that giving it a relative/auto width
  // instead would make IT dictate the shared column's width. See ListPanel.jsx.
  const dateNavRef = useRef(null)
  const [listWidth, setListWidth] = useState(null)
  useLayoutEffect(() => {
    const el = dateNavRef.current
    if (!el) return
    // getBoundingClientRect (border-box) rather than entry.contentRect (which
    // excludes DateNav's own padding, undershooting the width to match).
    const observer = new ResizeObserver(() => setListWidth(el.getBoundingClientRect().width))
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  function toggleDonationType(type) {
    setDonationTypes(types => ({ ...types, [type]: !types[type] }))
  }

  // The "Abierto ahora" tab selects selectedDate = null (see DateNav) — when
  // active, only show points that are actually open right now.
  const showOnlyOpenNow = selectedDate === null
  const filterByOpenNow = features =>
    showOnlyOpenNow
      ? features.filter(f => getOpenStatus(f.properties?.opening_hours, now)?.isOpen === true)
      : features

  // A point supports "sangre" (whole blood) implicitly unless plasma/médula flags
  // say otherwise — see getPointInfo in lib/pointHelpers.js.
  const filterByDonationType = features =>
    features.filter(f => {
      const p = f.properties ?? {}
      return (
        donationTypes.sangre ||
        (donationTypes.plasma && Boolean(p.plasma)) ||
        (donationTypes.medula && Boolean(p.medula))
      )
    })

  // Bucketed to the minute, and only ticking at all while "Abierto ahora" is
  // active, so the memos below don't get invalidated by the clock when the
  // open-now filter isn't even in play.
  const openNowMinute = showOnlyOpenNow ? Math.floor(now.getTime() / 60_000) : null

  // Memoized so MapView's marker-rebuild effects (keyed on these arrays) don't fire
  // on every render — e.g. after a flyTo's moveend updates mapCenter — which was
  // resetting the selected marker's red highlight before its own effect could reapply it.
  const visibleFixedPoints = useMemo(
    () => filterByDonationType(filterByOpenNow(fixedPoints)),
    [fixedPoints, showOnlyOpenNow, openNowMinute, donationTypes]
  )
  const visibleMobilePoints = useMemo(
    () => filterByDonationType(filterByOpenNow(showOnlyFixed ? [] : mobilePoints)),
    [mobilePoints, showOnlyOpenNow, openNowMinute, donationTypes, showOnlyFixed]
  )


  return (
    <div className="flex flex-col h-screen bg-white">
      <Header />
      <div className="flex flex-1 overflow-hidden relative">
        <div className="flex-1 relative">
          <MapView
            fixedPoints={visibleFixedPoints}
            mobilePoints={visibleMobilePoints}
            selectedPoint={selectedPoint}
            onSelectPoint={setSelectedPoint}
            onUserLocation={setUserLocation}
            onCenterChange={setMapCenter}
          />
          {selectedPoint && (
            <Popup point={selectedPoint} onClose={() => setSelectedPoint(null)} />
          )}
        </div>

        {/* Floating controls: date tabs + list on the left, filter chips on the
            right — all overlaid on top of the full-width map. */}
        <div className="absolute inset-4 z-10 flex flex-col md:flex-row md:items-start md:justify-between gap-3 pointer-events-none">
          <div
            className="flex flex-col gap-3 pointer-events-auto min-w-0 h-full"
            style={listWidth ? { '--list-width': `${listWidth}px` } : undefined}
          >
            <DateNav ref={dateNavRef} selectedDate={selectedDate} onSelectDate={setSelectedDate} />
            {showList ? (
              <ListPanel
                fixedPoints={visibleFixedPoints}
                mobilePoints={visibleMobilePoints}
                selectedPoint={selectedPoint}
                onSelectPoint={setSelectedPoint}
                onClose={() => setShowList(false)}
                refPoint={userLocation ?? mapCenter}
                locationGranted={userLocation !== null}
              />
            ) : (
              <button
                onClick={() => setShowList(true)}
                className="self-start bg-white rounded-full px-4 py-2 shadow-md text-sm font-medium flex items-center gap-2 hover:bg-gray-50 transition-colors"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="3" y1="6" x2="21" y2="6" />
                  <line x1="3" y1="12" x2="21" y2="12" />
                  <line x1="3" y1="18" x2="21" y2="18" />
                </svg>
                Mostrar lista
              </button>
            )}
          </div>
          <div className="pointer-events-auto">
            <FilterChips
              donationTypes={donationTypes}
              onToggleDonationType={toggleDonationType}
              showOnlyFixed={showOnlyFixed}
              onToggleFixed={() => setShowOnlyFixed(v => !v)}
            />
          </div>
        </div>
      </div>
    </div>
  )
}
