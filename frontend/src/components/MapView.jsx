import { useEffect, useRef } from 'react'
import maplibregl from 'maplibre-gl'

const MADRID_CENTER = [-3.7, 40.4]
const INITIAL_ZOOM = 10

const BUS_PATH =
  'M4 16c0 .88.39 1.67 1 2.22V20c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-1h8v1c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-1.78c.61-.55 1-1.34 1-2.22V6c0-3.5-3.58-4-8-4s-8 .5-8 4v10zm3.5 1c-.83 0-1.5-.67-1.5-1.5S6.67 14 7.5 14s1.5.67 1.5 1.5S8.33 17 7.5 17zm9 0c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5zm1.5-6H6V6h12v5z'

// Hospital building: L-shaped outline (tall main section + shorter wing), cross, door
function hospitalSvg(color) {
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M3 22V4h11v6h7v12H3"/>
    <path d="M6.5 9h4M8.5 7v4"/>
    <path d="M7 22v-4h3v4"/>
  </svg>`
}

function busSvg(color) {
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="18" height="18" fill="${color}">
    <path d="${BUS_PATH}"/>
  </svg>`
}

function makeMarkerEl(isFixed, isSelected) {
  const el = document.createElement('div')
  const border = isSelected ? '#dc2626' : '#111827'
  const bg = isSelected ? '#dc2626' : '#ffffff'
  const color = isSelected ? '#ffffff' : '#111827'
  el.style.cssText = `
    width:36px;height:36px;border-radius:50%;
    border:2px solid ${border};background:${bg};
    display:flex;align-items:center;justify-content:center;
    cursor:pointer;box-shadow:0 1px 4px rgba(0,0,0,.25);
    transition:border-color .15s,background .15s;
  `
  el.innerHTML = isFixed ? hospitalSvg(color) : busSvg(color)
  return el
}

function applyMarkerStyle(el, isFixed, isSelected) {
  const border = isSelected ? '#dc2626' : '#111827'
  const bg = isSelected ? '#dc2626' : '#ffffff'
  const color = isSelected ? '#ffffff' : '#111827'
  el.style.borderColor = border
  el.style.background = bg
  const svg = el.querySelector('svg')
  if (isFixed) {
    svg.setAttribute('stroke', color)
  } else {
    svg.setAttribute('fill', color)
  }
}

function buildMarkers(features, isFixed, map, onSelect) {
  return features.map(feature => {
    const [lng, lat] = feature.geometry.coordinates
    const el = makeMarkerEl(isFixed, false)
    el.addEventListener('click', e => {
      e.stopPropagation()
      onSelect(feature)
    })
    const marker = new maplibregl.Marker({ element: el }).setLngLat([lng, lat]).addTo(map)
    return { marker, feature, el, isFixed }
  })
}

export default function MapView({ fixedPoints, mobilePoints, selectedPoint, onSelectPoint, onUserLocation, onCenterChange }) {
  const containerRef = useRef(null)
  const mapRef = useRef(null)
  const fixedRef = useRef([])
  const mobileRef = useRef([])

  useEffect(() => {
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: 'https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json',
      center: MADRID_CENTER,
      zoom: INITIAL_ZOOM,
    })
    map.addControl(new maplibregl.NavigationControl(), 'top-right')
    const geolocate = new maplibregl.GeolocateControl({
      positionOptions: { enableHighAccuracy: true },
      trackUserLocation: true,
      showUserLocation: true,
      fitBoundsOptions: { maxZoom: 12 },
    })
    map.addControl(geolocate, 'top-right')

    geolocate.on('geolocate', e => {
      onUserLocation?.({ lat: e.coords.latitude, lng: e.coords.longitude })
    })

    map.on('load', async () => {
      // Auto-trigger if permission was already granted — no prompt, no extra dot
      try {
        const status = await navigator.permissions?.query({ name: 'geolocation' })
        if (status?.state === 'granted') geolocate.trigger()
      } catch (_) {}
    })

    map.on('click', () => onSelectPoint(null))
    map.on('moveend', () => {
      const { lat, lng } = map.getCenter()
      onCenterChange?.({ lat, lng })
    })
    mapRef.current = map
    onCenterChange?.({ lat: MADRID_CENTER[1], lng: MADRID_CENTER[0] })
    return () => map.remove()
  }, [])

  useEffect(() => {
    if (!mapRef.current) return
    fixedRef.current.forEach(({ marker }) => marker.remove())
    fixedRef.current = buildMarkers(fixedPoints, true, mapRef.current, onSelectPoint)
  }, [fixedPoints])

  useEffect(() => {
    if (!mapRef.current) return
    mobileRef.current.forEach(({ marker }) => marker.remove())
    mobileRef.current = buildMarkers(mobilePoints, false, mapRef.current, onSelectPoint)
  }, [mobilePoints])

  // Update marker styles when selection changes without recreating markers
  useEffect(() => {
    const all = [...fixedRef.current, ...mobileRef.current]
    all.forEach(({ feature, el, isFixed }) => {
      applyMarkerStyle(el, isFixed, feature === selectedPoint)
    })
    if (selectedPoint && mapRef.current) {
      const [lng, lat] = selectedPoint.geometry.coordinates
      mapRef.current.flyTo({ center: [lng, lat], zoom: 14, offset: [0, 80], duration: 500 })
    }
  }, [selectedPoint])

  return <div ref={containerRef} className="w-full h-full" />
}
