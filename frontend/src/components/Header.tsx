import { Link } from 'react-router-dom'

export default function Header() {
  return (
    <header className="flex items-center justify-between">
      <Link to="/" className="flex items-center gap-2 text-sm font-medium no-underline text-text">
        <span className="flex h-8 w-8 items-center justify-center rounded-md border border-primary/40 bg-primary/15 text-primary">
          ♡
        </span>
        HeartLens
      </Link>
      <span className="inline-flex items-center rounded-full border border-border bg-bg-card px-2.5 py-1 text-xs text-text-muted">
        专业分析
      </span>
    </header>
  )
}
