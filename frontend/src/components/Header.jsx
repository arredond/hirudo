export default function Header() {
  return (
    <header className="flex items-center px-6 py-4 border-b border-gray-200 shrink-0">
      <div className="text-2xl font-bold tracking-tight select-none">
        <span className="text-black">donde</span>
        <span className="text-red-600">donar</span>
      </div>
      <div className="w-px h-8 bg-gray-200 mx-6" />
      <p className="text-sm text-gray-500 max-w-xs leading-snug">
        Estés donde estés encuentra tu punto de donación más cercano.
      </p>
    </header>
  )
}
