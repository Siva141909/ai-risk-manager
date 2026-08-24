import { relationshipTypeLabel } from '../../utils/format'

export function GraphLegend({ types, colorFor }: { types: string[]; colorFor: (type: string) => string }) {
  if (types.length === 0) return null
  return (
    <div className="graph-legend">
      {types.map((type) => (
        <span key={type} className="graph-legend-item">
          <span className="graph-legend-swatch" style={{ background: colorFor(type) }} />
          {relationshipTypeLabel(type)}
        </span>
      ))}
    </div>
  )
}
