export default function ErrorMessage({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16">
      <div className="w-12 h-12 rounded-full bg-danger/10 flex items-center justify-center text-2xl">!</div>
      <p className="text-sm text-danger">{message}</p>
    </div>
  )
}
