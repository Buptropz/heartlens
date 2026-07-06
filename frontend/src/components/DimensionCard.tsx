import type { DimensionCard as DC } from '../lib/types'

const DIM_COLORS: Record<string, string> = {
  sincerity: '#8b7cf0',
  engagement: '#a78bfa',
  respect: '#fcd34d',
  manipulation: '#fda4af',
  communication: '#67e8f9',
  red_flags: '#fb7185',
}

export default function DimensionCard({ card }: { card: DC }) {
  const color = DIM_COLORS[card.dimension] || '#8b7cf0'

  return (
    <div className="rounded-xl border border-border bg-bg-card p-5">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-xs px-2 py-0.5 rounded-full" style={{ backgroundColor: color + '20', color }}>
          {card.title.split('：')[0]}
        </span>
      </div>
      <h3 className="text-base font-semibold mb-2">{card.title}</h3>
      <p className="text-sm text-text-muted leading-relaxed mb-3">{card.summary}</p>

      {card.evidence.map((ev, i) => (
        <div key={i} className="mb-2 pl-3 border-l-2" style={{ borderColor: color + '60' }}>
          <p className="text-sm text-text italic">"{ev.quote}"</p>
          <p className="text-xs text-text-muted mt-0.5">↗ {ev.analysis}</p>
        </div>
      ))}

      <div className="mt-3 pt-3 border-t border-border">
        <p className="text-xs text-text-muted leading-relaxed">
          <span className="font-medium text-text">💡 </span>
          {card.suggestion}
        </p>
      </div>
    </div>
  )
}
