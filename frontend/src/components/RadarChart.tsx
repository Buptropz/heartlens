import type { RadarData } from '../lib/types'

const DIMS = [
  { key: 'sincerity' as const, angle: -90, color: '#8b7cf0' },
  { key: 'engagement' as const, angle: -30, color: '#a78bfa' },
  { key: 'respect' as const, angle: 30, color: '#fcd34d' },
  { key: 'manipulation' as const, angle: 90, color: '#fda4af' },
  { key: 'communication' as const, angle: 150, color: '#67e8f9' },
  { key: 'red_flags' as const, angle: 210, color: '#fb7185' },
]

export default function RadarChart({ data }: { data: RadarData }) {
  const size = 280
  const cx = size / 2
  const cy = size / 2
  const maxR = 110

  const toXY = (angleDeg: number, value: number) => {
    const rad = (angleDeg * Math.PI) / 180
    const r = (value / 100) * maxR
    return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) }
  }

  const points = DIMS.map(d => toXY(d.angle, data[d.key].score))
  const polygonPoints = points.map(p => `${p.x},${p.y}`).join(' ')

  return (
    <div className="flex justify-center">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        {/* Grid rings */}
        {[0.25, 0.5, 0.75, 1].map(scale => (
          <polygon
            key={scale}
            points={DIMS.map(d => {
              const p = toXY(d.angle, scale * 100)
              return `${p.x},${p.y}`
            }).join(' ')}
            fill="none"
            stroke="rgba(255,255,255,0.06)"
            strokeWidth="1"
          />
        ))}
        {/* Axis lines */}
        {DIMS.map(d => {
          const p = toXY(d.angle, 100)
          return <line key={d.key} x1={cx} y1={cy} x2={p.x} y2={p.y} stroke="rgba(255,255,255,0.06)" strokeWidth="1" />
        })}
        {/* Data polygon */}
        <polygon points={polygonPoints} fill="rgba(139,124,240,0.15)" stroke="#8b7cf0" strokeWidth="1.5" />
        {/* Data points */}
        {points.map((p, i) => (
          <circle key={i} cx={p.x} cy={p.y} r="3" fill={DIMS[i].color} />
        ))}
        {/* Labels */}
        {DIMS.map(d => {
          const labelR = maxR + 24
          const rad = (d.angle * Math.PI) / 180
          const lx = cx + labelR * Math.cos(rad)
          const ly = cy + labelR * Math.sin(rad)
          return (
            <text key={d.key} x={lx} y={ly} textAnchor="middle" dominantBaseline="middle"
              fill={d.color} fontSize="11" fontWeight="500" fontFamily="system-ui, sans-serif">
              {data[d.key].label}
            </text>
          )
        })}
        {/* Center score */}
        <text x={cx} y={cy - 4} textAnchor="middle" fill="white" fontSize="14" fontWeight="600" fontFamily="system-ui, sans-serif">
          综合
        </text>
      </svg>
    </div>
  )
}
