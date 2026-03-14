import { Link } from 'react-router-dom'

export function TopBanner() {
  return (
    <header className="sticky top-0 z-50 border-b border-primary/70 bg-primary">
      <div className="container mx-auto flex h-14 max-w-4xl items-center px-6">
        <Link to="/dashboard" className="flex items-center gap-2.5">
          <img
            src="/logo.png"
            alt="Our Table"
            className="h-8 w-8 rounded-full object-cover"
          />
          <span className="text-xl font-semibold tracking-[-0.02em] text-primary-foreground lowercase">
            our table
          </span>
        </Link>
      </div>
    </header>
  )
}
