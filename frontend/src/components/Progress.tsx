export function Progress({
  value,
  tone = "brand",
  className = "",
}: {
  value: number; // 0..1
  tone?: "brand" | "success" | "warning" | "danger";
  className?: string;
}) {
  const pct = Math.max(0, Math.min(1, value)) * 100;
  const color =
    tone === "success" ? "bg-success" :
    tone === "warning" ? "bg-warning" :
    tone === "danger"  ? "bg-danger"  : "bg-brand";
  return (
    <div className={`h-1.5 bg-bg-2 rounded-full overflow-hidden ${className}`}>
      <span className={`block h-full ${color}`} style={{ width: `${pct}%` }} />
    </div>
  );
}
