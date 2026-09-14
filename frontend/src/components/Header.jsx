import BloodLevelBadges from './BloodLevelBadges'

// hideOnMobile: the mobile list panel is a fixed, full-screen overlay meant to
// sit above everything else in the app — including this header. In practice it
// doesn't always paint above it (stacking-context quirks vary by browser), so
// instead of relying on z-index alone we just remove the header from mobile
// layout while the list overlay is open, guaranteeing its search bar and close
// button stay reachable. Desktop is unaffected (the list is a side panel there).
export default function Header({ hideOnMobile = false }) {
  return (
    <header
      className={`${hideOnMobile ? 'hidden md:flex' : 'flex'} items-center justify-between gap-3 px-4 py-3 sm:px-6 sm:py-4 border-b border-gray-200 shrink-0`}
    >
      <div className="flex items-center min-w-0 shrink-0">
        <div className="text-lg sm:text-2xl font-bold tracking-tight select-none shrink-0">
          <span className="text-black">donde</span>
          <span className="text-red-600">donar</span>
        </div>
      </div>
      <BloodLevelBadges />
    </header>
  )
}
