import { getPointInfo } from '../lib/pointHelpers'
import { isPermanentlyClosed, isTemporarilyClosed } from '../lib/openingHours'
import OpenStatusBadge from './OpenStatusBadge'

const DONATION_TYPE_LABELS = { plasma: 'Plasma', sangre: 'Sangre', medula: 'Médula' }

function Row({ icon, children }) {
  return (
    <div className="flex items-start gap-2 text-sm text-gray-700">
      <span className="mt-0.5 shrink-0 text-gray-400">{icon}</span>
      <span>{children}</span>
    </div>
  )
}

const PinIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z" />
  </svg>
)

const ClockIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
    <path d="M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67V7z" />
  </svg>
)

const InfoIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z" />
  </svg>
)

export default function Popup({ point, onClose }) {
  const { isMobile, name, address, locality, hours, openingHours, mapsUrl, infoUrl, roomLocation, donorInfo, notes, zipCode, donationTypes } = getPointInfo(point)
  const closedPermanently = isPermanentlyClosed(openingHours)
  const closedTemporarily = isTemporarilyClosed(openingHours)

  const fullAddress = [address, locality, zipCode].filter(Boolean).join(', ')
  const activeDonationTypes = Object.entries(donationTypes)
    .filter(([, active]) => active)
    .map(([type]) => type)

  return (
    <div className={`absolute bottom-4 left-4 right-4 md:left-auto md:right-6 md:w-80 z-20 bg-white rounded-2xl shadow-xl overflow-hidden ${closedPermanently ? 'opacity-75 grayscale' : ''} ${closedTemporarily ? 'opacity-75' : ''}`}>
      <div className="p-5">
        <div className="flex items-start justify-between mb-3">
          <div>
            <p className="text-xs text-gray-400 uppercase tracking-wide mb-0.5">
              {isMobile ? 'Punto móvil' : 'Punto fijo'}
            </p>
            <h2 className="text-base font-semibold text-gray-900 leading-snug">{name}</h2>
            {closedPermanently ? (
              <p className="text-xs font-medium text-gray-500 mt-0.5">Cerrado permanentemente</p>
            ) : (
              <div className="mt-0.5">
                <OpenStatusBadge openingHours={openingHours} />
              </div>
            )}
            {activeDonationTypes.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mt-2">
                {activeDonationTypes.map(type => (
                  <span
                    key={type}
                    className="text-xs font-medium text-gray-600 bg-gray-100 rounded-full px-2.5 py-0.5"
                  >
                    {DONATION_TYPE_LABELS[type]}
                  </span>
                ))}
              </div>
            )}
          </div>
          <button
            onClick={onClose}
            className="ml-3 shrink-0 text-gray-400 hover:text-gray-600 transition-colors"
            aria-label="Cerrar"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <div className="space-y-2">
          {fullAddress && <Row icon={<PinIcon />}>{fullAddress}</Row>}
          {roomLocation && <Row icon={<PinIcon />}>{roomLocation}</Row>}
          {hours && <Row icon={<ClockIcon />}>{hours}</Row>}
          {donorInfo && <Row icon={<InfoIcon />}>{donorInfo}</Row>}
          {notes && (
            <p className="text-xs text-gray-500 pl-6 leading-relaxed">{notes}</p>
          )}
        </div>
      </div>

      {(mapsUrl || infoUrl) && (
        <div className={`px-5 pb-5 grid gap-2 ${mapsUrl && infoUrl ? 'grid-cols-2' : 'grid-cols-1'}`}>
          {mapsUrl && (
            <a
              href={mapsUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="block text-center border-2 border-gray-900 text-gray-900 rounded-xl py-2.5 text-sm font-medium hover:bg-gray-900 hover:text-white transition-colors"
            >
              Cómo llegar
            </a>
          )}
          {infoUrl && (
            <a
              href={infoUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="block text-center border-2 border-gray-300 text-gray-700 rounded-xl py-2.5 text-sm font-medium hover:bg-gray-100 transition-colors"
            >
              + info
            </a>
          )}
        </div>
      )}
    </div>
  )
}
