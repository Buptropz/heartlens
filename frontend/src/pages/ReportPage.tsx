import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import Header from '../components/Header'
import Footer from '../components/Footer'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'
import CopyButton from '../components/CopyButton'
import Toast from '../components/Toast'
import RadarChart from '../components/RadarChart'
import DimensionCard from '../components/DimensionCard'
import { getReport } from '../lib/api'
import type { AnalyzeResponse } from '../lib/types'

export default function ReportPage() {
  const { id } = useParams<{ id: string }>()
  const [report, setReport] = useState<AnalyzeResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [toast, setToast] = useState('')

  useEffect(() => {
    if (!id) return
    getReport(id)
      .then(setReport)
      .catch(err => setError(err?.detail || '加载报告失败'))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) return <main className="min-h-svh px-5 py-6"><LoadingSpinner text="加载报告中..." /></main>
  if (error) return <main className="min-h-svh px-5 py-6"><ErrorMessage message={error} /></main>
  if (!report) return null

  const shareUrl = `${window.location.origin}/report/${report.report_id}`

  return (
    <main className="relative min-h-svh overflow-hidden px-5 py-6">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-24 bg-primary/10 blur-3xl" />

      <section className="relative z-10 mx-auto min-h-[calc(100svh-3rem)] w-full max-w-2xl flex flex-col">
        <div className="flex items-center justify-between mb-8">
          <Link to="/" className="text-sm text-text-muted hover:text-text transition">← 重新分析</Link>
          <CopyButton text={shareUrl} />
        </div>

        <Header />

        <div className="flex-1 py-8 space-y-6">
          {/* Radar chart */}
          <RadarChart data={report.radar} />

          {/* Overall assessment */}
          <div className="rounded-xl border border-border bg-bg-card p-5">
            <h3 className="text-sm font-semibold mb-2">综合评估</h3>
            <p className="text-sm text-text-muted leading-relaxed">{report.overall}</p>
          </div>

          {/* Dimension cards */}
          {report.cards.map((card, i) => (
            <DimensionCard key={card.dimension || i} card={card} />
          ))}
        </div>

        <Footer />
      </section>

      {toast && <Toast message={toast} onClose={() => setToast('')} />}
    </main>
  )
}
