export default function Loading({ text = 'Loading...' }: { text?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-20">
      <div className="w-10 h-10 border-4 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin" />
      <p className="mt-4 text-sm text-[var(--color-text-secondary)]">{text}</p>
    </div>
  )
}
