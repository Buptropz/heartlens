export default function RadarScanBg() {
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden">
      {/* Concentric rings */}
      <div className="absolute top-1/2 left-[8%] -translate-y-1/2 w-[300px] h-[300px]">
        <div className="absolute inset-0 rounded-full border border-primary/10" />
        <div className="absolute inset-8 rounded-full border border-primary/8" />
        <div className="absolute inset-16 rounded-full border border-primary/5" />
        {/* Scan arm */}
        <div className="absolute inset-0 rounded-full overflow-hidden">
          <div
            className="absolute top-0 left-1/2 w-1/2 h-full origin-left animate-[spin_4s_linear_infinite]"
            style={{
              background: 'conic-gradient(from 0deg, transparent 0deg, rgba(139,124,240,0.15) 15deg, transparent 30deg)',
            }}
          />
        </div>
        {/* Center dot */}
        <div className="absolute top-1/2 left-1/2 w-2 h-2 -translate-x-1/2 -translate-y-1/2 rounded-full bg-primary shadow-[0_0_16px_#8b7cf0]" />
        {/* Pulse rings */}
        <div className="absolute -inset-4 rounded-full border border-primary/10 animate-[pulse-ring_2s_ease-out_infinite]" />
        <div className="absolute -inset-4 rounded-full border border-primary/8 animate-[pulse-ring_2s_ease-out_0.7s_infinite]" />
        {/* Floating labels */}
        <span className="absolute top-[12%] left-[78%] text-[10px] text-primary-light whitespace-nowrap">真诚度</span>
        <span className="absolute top-[52%] left-[90%] text-[10px] text-primary whitespace-nowrap">投入</span>
        <span className="absolute top-[82%] left-[52%] text-[10px] text-accent whitespace-nowrap">红旗</span>
        <span className="absolute top-[28%] left-[52%] text-[10px] text-primary whitespace-nowrap">尊重</span>
        <span className="absolute top-[62%] left-[20%] text-[10px] text-danger whitespace-nowrap">冷暴力</span>
      </div>
    </div>
  )
}
