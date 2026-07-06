import { useEffect, useState } from 'react'

export default function Toast({ message, onClose }: { message: string; onClose: () => void }) {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    setVisible(true)
    const timer = setTimeout(() => { setVisible(false); setTimeout(onClose, 300) }, 2500)
    return () => clearTimeout(timer)
  }, [onClose])

  return (
    <div className={`fixed bottom-6 left-1/2 -translate-x-1/2 z-50 transition-all duration-300 ${
      visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
    }`}>
      <div className="bg-primary/90 text-white px-4 py-2 rounded-lg text-sm shadow-lg">
        {message}
      </div>
    </div>
  )
}
