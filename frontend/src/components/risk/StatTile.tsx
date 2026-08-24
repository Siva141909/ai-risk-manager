import './risk.css'

export function StatTile({
  label,
  value,
  accentColor,
}: {
  label: string
  value: string | number
  accentColor?: string
}) {
  return (
    <div className="stat-tile" style={accentColor ? { borderLeft: `4px solid ${accentColor}` } : undefined}>
      <div className="stat-tile-value">{value}</div>
      <div className="stat-tile-label">{label}</div>
    </div>
  )
}
