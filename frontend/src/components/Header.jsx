import BloodLevelBadges from './BloodLevelBadges'

export default function Header() {
  return (
    <header className="flex items-center justify-between gap-4 px-6 py-4 border-b border-gray-200 shrink-0">
      <div className="flex items-center min-w-0">
        <div className="text-2xl font-bold tracking-tight select-none shrink-0">
          <span className="text-black">donde</span>
          <span className="text-red-600">donar</span>
          <span className="text-black">sangre.es</span>
        </div>
      </div>
      <BloodLevelBadges />
    </header>
  )
}
