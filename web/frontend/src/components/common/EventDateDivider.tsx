export function EventDateDivider({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-2 py-1.5">
      <div className="h-px flex-1 bg-border" />
      <span className="text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
        {label}
      </span>
      <div className="h-px flex-1 bg-border" />
    </div>
  )
}
