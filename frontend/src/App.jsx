import { useState, useMemo, useRef, useLayoutEffect, useEffect } from 'react'
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
import { regionAt, nearestCoveredRegion } from './lib/regions'

dayjs.locale('es')

export default function App() {
  // Defaults: "Abierto ahora" tab (selectedDate = null, see DateNav) and the
  // "Sangre" filter chip.
  const [selectedDate, setSelectedDate] = useState(null)
  const [selectedPoint, setSelectedPoint] = useState(null)
  const [showList, setShowList] = useState(false)
  const [showOnlyFixed, setShowOnlyFixed] = useState(false)
  // Single-select, not independent toggles: every point takes whole blood, but
  // plasma/médula are only taken at a handful of points, so showing "sangre OR
  // plasma OR médula" together read as noise in practice. One donation type is
  // active at a time, radio-style.
  const [donationType, setDonationType] = useState('sangre')
  const [userLocation, setUserLocation] = useState(null)
  const [mapCenter, setMapCenter] = useState({ lat: 40.4, lng: -3.7 })

  const { fixedPoints, mobilePoints, loadingMobile } = useBloodPoints(selectedDate)
  const now = useNowTick()

  // The list panel should match DateNav's own (content-driven) width — measured
  // rather than duplicated as a literal, since ListPanel's own content (long
  // addresses, buttons, ...) is wide enough that giving it a relative/auto width
  // instead would make IT dictate the shared column's width. See ListPanel.jsx.
  const dateNavRef = useRef(null)
  const mapViewRef = useRef(null)
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

  // The "Abierto ahora" tab selects selectedDate = null (see DateNav) — when
  // active, only show points that are actually open right now.
  const showOnlyOpenNow = selectedDate === null
  const filterByOpenNow = features =>
    showOnlyOpenNow
      ? features.filter(f => getOpenStatus(f.properties?.opening_hours, now)?.isOpen === true)
      : features

  // Every point takes "sangre" (whole blood) implicitly; plasma/médula are only
  // taken where the corresponding flag is set — see getPointInfo in lib/pointHelpers.js.
  const filterByDonationType = features =>
    donationType === 'sangre' ? features : features.filter(f => Boolean(f.properties?.[donationType]))

  // Bucketed to the minute, and only ticking at all while "Abierto ahora" is
  // active, so the memos below don't get invalidated by the clock when the
  // open-now filter isn't even in play.
  const openNowMinute = showOnlyOpenNow ? Math.floor(now.getTime() / 60_000) : null

  // Everything below the date/"solo puntos fijos" filters but above the
  // donation-type filter — shared by the visible points (further narrowed to
  // the selected type) and the per-type counts shown on the chips (which need
  // every type's count regardless of which one is currently selected).
  const openNowFixedPoints = useMemo(
    () => filterByOpenNow(fixedPoints),
    [fixedPoints, showOnlyOpenNow, openNowMinute]
  )
  const openNowMobilePoints = useMemo(
    () => filterByOpenNow(showOnlyFixed ? [] : mobilePoints),
    [mobilePoints, showOnlyOpenNow, openNowMinute, showOnlyFixed]
  )

  const donationTypeCounts = useMemo(() => {
    const all = [...openNowFixedPoints, ...openNowMobilePoints]
    return {
      sangre: all.length,
      plasma: all.filter(f => Boolean(f.properties?.plasma)).length,
      medula: all.filter(f => Boolean(f.properties?.medula)).length,
    }
  }, [openNowFixedPoints, openNowMobilePoints])

  // Memoized so MapView's marker-rebuild effects (keyed on these arrays) don't fire
  // on every render — e.g. after a flyTo's moveend updates mapCenter — which was
  // resetting the selected marker's red highlight before its own effect could reapply it.
  const visibleFixedPoints = useMemo(
    () => filterByDonationType(openNowFixedPoints),
    [openNowFixedPoints, donationType]
  )
  const visibleMobilePoints = useMemo(
    () => filterByDonationType(openNowMobilePoints),
    [openNowMobilePoints, donationType]
  )

  // Plasma/médula points are a handful out of the full list — easy to miss if the
  // map happens to be zoomed into an area that doesn't include any of them. Médula
  // is taken at exactly one point (see puntos_fijos_otras_donaciones.json), so
  // rather than just fitting it like any other single marker, select it
  // automatically; MapView frames it together with userLocation via focusCompanion
  // below (whenever it's known — including if it resolves after this selection).
  useEffect(() => {
    if (donationType !== 'medula') return
    const centro = fixedPoints.find(f => Boolean(f.properties?.medula))
    if (centro) setSelectedPoint(centro)
  }, [donationType, fixedPoints])

  // Plasma: just zoom out to fit whatever's currently visible, once, right when
  // the filter is picked — deliberately not re-fit on every later points update
  // while it stays selected, so it doesn't fight the user's own panning/zooming.
  useEffect(() => {
    if (donationType !== 'plasma') return
    const coords = [...visibleFixedPoints, ...visibleMobilePoints].map(f => f.geometry.coordinates)
    mapViewRef.current?.fitToCoords(coords)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [donationType])

  // The region named in the header title (and driving which region's blood
  // levels are fetched) — whichever region's real boundary the map center
  // currently falls inside (see regionAt in lib/regions.js), falling back to
  // the nearest covered region's fixed point when it's outside both (e.g.
  // panned elsewhere in Spain), using every fixed point regardless of
  // filters so that fallback never goes stale just because a filter hides
  // them all.
  const currentRegion = useMemo(
    () => regionAt(mapCenter) ?? nearestCoveredRegion(fixedPoints, mapCenter),
    [fixedPoints, mapCenter]
  )

  // Selecting a region from the header's dropdown jumps the map there instead
  // of tracking a separately-held "selected region" — nearestRegion then picks
  // it back up on its own once the map settles (moveend), same as panning
  // there by hand would.
  const handleSelectRegion = region => {
    const coords = fixedPoints
      .filter(f => f.properties?.region === region)
      .map(f => f.geometry.coordinates)
    mapViewRef.current?.fitToCoords(coords)
  }

  return (
    <div className="flex flex-col h-screen bg-white">
      <Header
        hideOnMobile={showList}
        donationType={donationType}
        onSelectDonationType={setDonationType}
        region={currentRegion}
        onSelectRegion={handleSelectRegion}
      />
      <div className="flex flex-1 overflow-hidden relative">
        <div className="flex-1 relative">
          <MapView
            ref={mapViewRef}
            fixedPoints={visibleFixedPoints}
            mobilePoints={visibleMobilePoints}
            selectedPoint={selectedPoint}
            onSelectPoint={setSelectedPoint}
            onUserLocation={setUserLocation}
            onCenterChange={setMapCenter}
            focusCompanion={donationType === 'medula' ? userLocation : null}
          />
          {selectedPoint && (
            <Popup point={selectedPoint} onClose={() => setSelectedPoint(null)} />
          )}
        </div>

        {/* Floating controls: date tabs + list on the left, filter chips on the
            right — all overlaid on top of the full-width map. */}
        <div className="absolute inset-4 z-10 flex flex-col md:flex-row md:items-start md:justify-between gap-3 pointer-events-none">
          <div
            // max-w leaves clearance on mobile for the map's own geolocate button,
            // which sits in the same top-right corner (see MapView.jsx) — DateNav's
            // own overflow-x-auto lets its tabs scroll instead of running under it.
            className="flex flex-col gap-3 pointer-events-auto min-w-0 max-w-[calc(100%-3.5rem)] md:max-w-none md:h-full"
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
          {/* Mobile: pinned to the bottom edge instead of flowing after the date
              tabs, which was crowding the middle of the map. Desktop keeps its
              spot at the top, opposite the date tabs (see the md: overrides). */}
          <div className="pointer-events-auto fixed inset-x-4 bottom-[calc(1rem+env(safe-area-inset-bottom))] z-10 md:static md:inset-auto md:bottom-auto md:z-auto">
            <FilterChips
              donationType={donationType}
              onSelectDonationType={setDonationType}
              counts={donationTypeCounts}
              showOnlyFixed={showOnlyFixed}
              onToggleFixed={() => setShowOnlyFixed(v => !v)}
            />
          </div>
        </div>
      </div>
    </div>
  )
}
