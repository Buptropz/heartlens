import { Link } from 'react-router-dom'
import Header from '../components/Header'

export default function ErrorPage() {
  return (
    <main className="min-h-svh px-5 py-6">
      <section className="mx-auto max-w-2xl">
        <Header />
        <div className="flex flex-col items-center justify-center py-24 gap-4">
          <p className="text-5xl">😕</p>
          <h2 className="text-xl font-semibold">页面出错了</h2>
          <p className="text-sm text-text-muted">请返回首页重试</p>
          <Link to="/" className="inline-flex items-center gap-2 rounded-lg bg-primary hover:bg-primary-dark transition text-white px-5 py-2 text-sm">
            返回首页
          </Link>
        </div>
      </section>
    </main>
  )
}
