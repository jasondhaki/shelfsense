export default function ZonePlaceholder({ title, note }: { title: string; note: string }) {
  return (
    <section aria-label={title} className="zone grid place-items-center">
      <div className="text-center">
        <h2 className="text-sm font-medium text-muted">{title}</h2>
        <p className="mt-1 text-xs text-muted/70">{note}</p>
      </div>
    </section>
  )
}
