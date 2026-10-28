import { useState, useEffect } from 'react'
import { medulaInfo } from '../lib/medula'
import { regionLink } from '../lib/regions'

// Shown while "médula" is the selected donation type: how to register as a
// bone marrow donor in the region the map is on, with its phone, sign-up form
// and official page. In most regions you phone or fill in a form first rather
// than just walking in, so this — not the map — is the main thing to show
// (see lib/medula.js). Collapsible to a pill so it doesn't hide the map;
// reopens whenever the region changes.
export default function MedulaInfoCard({ region }) {
  const [collapsed, setCollapsed] = useState(false)
  useEffect(() => setCollapsed(false), [region])

  const info = medulaInfo(region)
  const url = info.url ?? regionLink(region, 'medula')?.url

  if (collapsed) {
    return (
      <button
        onClick={() => setCollapsed(false)}
        className="bg-white rounded-full px-4 py-2 shadow-md text-sm font-medium hover:bg-gray-50 transition-colors"
      >
        Cómo hacerse donante de médula
      </button>
    )
  }

  return (
    <div className="bg-white rounded-2xl shadow-md p-4 md:w-80 text-left">
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm font-semibold text-gray-900">
          Hazte donante de médula{region ? ` en ${region}` : ''}
        </p>
        <button
          onClick={() => setCollapsed(true)}
          aria-label="Ocultar"
          className="-mt-1 -mr-1 p-1 text-gray-400 hover:text-gray-700 transition-colors"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>
      <p className="mt-1.5 text-sm text-gray-700">{info.summary}</p>
      <p className="mt-1.5 text-xs text-gray-500">Para registrarte necesitas tener entre 18 y 40 años.</p>
      <div className="mt-3 flex flex-wrap gap-2">
        {info.formUrl && (
          <a
            href={info.formUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-full bg-red-600 px-3.5 py-1.5 text-sm font-medium text-white hover:bg-red-700 transition-colors"
          >
            Inscríbete online
          </a>
        )}
        {info.phone && (
          <a
            // "983 328 000 ext. 89133" dials the extension after a pause (the comma)
            href={`tel:${info.phone.replace(/\s*ext\.?\s*/i, ',').replace(/\s/g, '')}`}
            className={`rounded-full px-3.5 py-1.5 text-sm font-medium transition-colors ${
              info.formUrl
                ? 'border border-gray-300 text-gray-800 hover:bg-gray-50'
                : 'bg-red-600 text-white hover:bg-red-700'
            }`}
          >
            Llamar al {info.phone}
          </a>
        )}
        {url && (
          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-full border border-gray-300 px-3.5 py-1.5 text-sm font-medium text-gray-800 hover:bg-gray-50 transition-colors"
          >
            Más información
          </a>
        )}
      </div>
    </div>
  )
}
