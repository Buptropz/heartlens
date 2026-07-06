import { Link } from 'react-router-dom'
import Header from '../components/Header'
import Footer from '../components/Footer'
import RadarScanBg from '../components/RadarScanBg'
import ParticleBg from '../components/ParticleBg'

const DIMS = ['真诚度', '投入程度', '尊重程度', '操纵倾向', '沟通健康度', '红旗指数']

export default function HomePage() {
  return (
    <main className="relative min-h-svh overflow-hidden px-5 py-6">
      <ParticleBg />
      <div className="pointer-events-none absolute inset-x-0 top-0 h-24 bg-primary/10 blur-3xl" />

      <section className="relative z-10 mx-auto flex min-h-[calc(100svh-3rem)] w-full max-w-5xl flex-col justify-between">
        <Header />

        <div className="grid gap-10 pb-8 pt-12 md:grid-cols-[1.05fr_0.95fr] md:items-center">
          <div>
            <div className="mb-5 flex flex-wrap gap-2">
              {DIMS.map(d => (
                <span key={d} className="inline-flex items-center rounded-full border border-primary/20 bg-primary/8 px-2.5 py-1 text-xs text-primary-light">
                  {d}
                </span>
              ))}
            </div>

            <h1 className="text-balance text-6xl font-semibold leading-[0.92] sm:text-7xl md:text-8xl">
              透过聊天<br/>看见真心
            </h1>

            <p className="mt-6 max-w-xl text-pretty text-lg leading-8 text-text-muted">
              基于心理学框架的 AI 关系洞察<br />
              每一个结论，都有对话中的原文依据
            </p>

            <div className="mt-9 flex flex-col gap-3 sm:flex-row">
              <Link
                to="/upload"
                className="inline-flex items-center justify-center gap-2 rounded-lg bg-primary hover:bg-primary-dark transition text-white px-6 py-3 text-sm font-medium shadow-[0_0_28px_rgba(139,124,240,0.22)]"
              >
                开始分析
                <span className="text-lg">→</span>
              </Link>
            </div>
          </div>

          <div className="relative mx-auto aspect-square w-full max-w-sm">
            <RadarScanBg />
          </div>
        </div>

        <Footer />
      </section>
    </main>
  )
}
