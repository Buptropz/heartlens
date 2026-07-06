import { useState, useRef, type FormEvent, type DragEvent, type ChangeEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import Header from '../components/Header'
import Footer from '../components/Footer'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'
import { analyze } from '../lib/api'

type InputTab = 'image' | 'text' | 'file'

export default function UploadPage() {
  const navigate = useNavigate()
  const [tab, setTab] = useState<InputTab>('image')
  const [images, setImages] = useState<File[]>([])
  const [text, setText] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [progress, setProgress] = useState(0)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const imageInputRef = useRef<HTMLInputElement>(null)

  const handleDrop = (e: DragEvent) => {
    e.preventDefault()
    const files = Array.from(e.dataTransfer.files).filter(f => f.type.startsWith('image/'))
    setImages(prev => [...prev, ...files].slice(0, 5))
  }

  const handleImageSelect = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setImages(prev => [...prev, ...Array.from(e.target.files!)].slice(0, 5))
    }
  }

  const removeImage = (i: number) => setImages(prev => prev.filter((_, idx) => idx !== i))

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    setProgress(10)

    const fd = new FormData()
    if (tab === 'image') {
      images.forEach(img => fd.append('images', img))
    } else if (tab === 'text') {
      fd.append('text', text)
    } else if (file) {
      fd.append('file', file)
    }
    fd.append('locale', 'zh-CN')

    try {
      setProgress(30)
      const result = await analyze(fd)
      setProgress(90)
      navigate(`/report/${result.report_id}`)
    } catch (err: any) {
      setError(err?.detail || '分析失败，请重试')
    } finally {
      setLoading(false)
      setProgress(0)
    }
  }

  return (
    <main className="relative min-h-svh overflow-hidden px-5 py-6">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-24 bg-primary/10 blur-3xl" />

      <section className="relative z-10 mx-auto min-h-[calc(100svh-3rem)] w-full max-w-2xl flex flex-col">
        <Header />

        <div className="flex-1 py-12">
          <h2 className="text-2xl font-semibold mb-8">开始分析</h2>

          {/* Tabs */}
          <div className="flex border-b border-border mb-6">
            {(['image', 'text', 'file'] as InputTab[]).map(t => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`px-4 py-2 text-sm border-b-2 transition ${
                  tab === t ? 'border-primary text-primary' : 'border-transparent text-text-muted'
                }`}
              >
                {t === 'image' ? '截图上传' : t === 'text' ? '粘贴文本' : '导入文件'}
              </button>
            ))}
          </div>

          {error && <ErrorMessage message={error} />}

          {loading ? (
            <div className="flex flex-col items-center gap-4 py-16">
              <LoadingSpinner text="正在分析中..." />
              <div className="w-full max-w-xs bg-border rounded-full h-2">
                <div className="bg-primary h-2 rounded-full transition-all duration-500" style={{ width: `${progress}%` }} />
              </div>
              <div className="text-xs text-text-muted space-y-1">
                <p className={progress >= 20 ? 'text-primary-light' : ''}>✓ 正在提取对话内容...</p>
                <p className={progress >= 50 ? 'text-primary-light' : ''}>⏳ 正在多维度分析...</p>
                <p className={progress >= 80 ? 'text-primary-light' : ''}>⏳ 正在生成报告...</p>
              </div>
            </div>
          ) : (
            <form onSubmit={handleSubmit}>
              {tab === 'image' && (
                <div
                  onDrop={handleDrop}
                  onDragOver={e => e.preventDefault()}
                  className="border-2 border-dashed border-border rounded-xl p-8 text-center hover:border-primary/40 transition cursor-pointer"
                  onClick={() => imageInputRef.current?.click()}
                >
                  <p className="text-3xl mb-2">📷</p>
                  <p className="text-sm text-text-muted mb-1">拖拽或点击上传聊天截图</p>
                  <p className="text-xs text-text-muted">支持 jpg/png/webp，最多 5 张</p>
                  <input ref={imageInputRef} type="file" accept="image/jpeg,image/png,image/webp" multiple hidden onChange={handleImageSelect} />

                  {images.length > 0 && (
                    <div className="flex gap-2 mt-4 flex-wrap justify-center">
                      {images.map((img, i) => (
                        <div key={i} className="relative w-16 h-16 rounded-lg overflow-hidden border border-border">
                          <img src={URL.createObjectURL(img)} alt="" className="w-full h-full object-cover" />
                          <button type="button" onClick={(e) => { e.stopPropagation(); removeImage(i) }}
                            className="absolute top-0 right-0 w-5 h-5 bg-danger text-white text-xs rounded-bl-lg">×</button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {tab === 'text' && (
                <div>
                  <textarea
                    value={text}
                    onChange={e => setText(e.target.value)}
                    placeholder="在此粘贴聊天文本内容..."
                    maxLength={20000}
                    className="w-full h-64 p-4 rounded-xl border border-border bg-bg-card text-text placeholder:text-text-muted/50 resize-none text-sm focus:outline-none focus:border-primary/50"
                  />
                  <p className={`text-xs mt-2 ${text.length > 20000 ? 'text-danger' : 'text-text-muted'}`}>
                    {text.length} / 20000
                  </p>
                </div>
              )}

              {tab === 'file' && (
                <div
                  className="border-2 border-dashed border-border rounded-xl p-8 text-center hover:border-primary/40 transition cursor-pointer"
                  onClick={() => fileInputRef.current?.click()}
                >
                  <p className="text-3xl mb-2">📄</p>
                  <p className="text-sm text-text-muted">点击选择聊天记录文件</p>
                  <p className="text-xs text-text-muted">支持 .txt / .json，最大 5MB</p>
                  <input ref={fileInputRef} type="file" accept=".txt,.json" hidden
                    onChange={e => setFile(e.target.files?.[0] || null)} />
                  {file && (
                    <p className="mt-3 text-sm text-primary-light">{file.name} ✓</p>
                  )}
                </div>
              )}

              <button
                type="submit"
                disabled={
                  (tab === 'image' && images.length === 0) ||
                  (tab === 'text' && !text.trim()) ||
                  (tab === 'file' && !file)
                }
                className="mt-6 w-full inline-flex items-center justify-center gap-2 rounded-lg bg-primary hover:bg-primary-dark disabled:opacity-40 disabled:cursor-not-allowed transition text-white px-6 py-3 text-sm font-medium"
              >
                开始分析 →
              </button>
            </form>
          )}
        </div>

        <Footer />
      </section>
    </main>
  )
}
