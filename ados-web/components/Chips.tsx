export function Chips({ items }: { items: string[] }) {
  if (items.length === 0) return <p className="text-[11.5px] text-mute">—</p>
  return (
    <div className="flex flex-wrap gap-1.5">
      {items.map((item) => (
        <span key={item} className="rounded-full bg-sidebar px-2 py-[3px] text-[11px] text-ink-soft">
          {item}
        </span>
      ))}
    </div>
  )
}
