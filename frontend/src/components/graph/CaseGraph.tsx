import { useMemo, useRef, useState, type WheelEvent, type MouseEvent as ReactMouseEvent } from 'react'
import type { CaseGraphResponse, GraphVizEdge } from '../../types/api'
import { relationshipTypeLabel } from '../../utils/format'
import { GraphLegend } from './GraphLegend'
import './graph.css'

// Deliberately far apart in hue (violet / cyan / orange) so all three
// remain distinguishable at a glance, unlike --color-accent (indigo)
// which reads too close to --color-graph-text (violet) at edge-stroke
// widths (docs/DESIGN_SYSTEM.md §8 — found during Phase 5B visual validation).
const RELATIONSHIP_COLORS: Record<string, string> = {
  SHARED_DEVICE: 'var(--color-graph-text)', // violet
  SHARED_IP: 'var(--color-graph-ip-text)', // cyan
  SHARED_BANK_ACCOUNT: 'var(--color-risk-high-text)', // orange
}

function relationshipColor(type: string): string {
  return RELATIONSHIP_COLORS[type] ?? 'var(--color-text-tertiary)'
}

interface Positioned {
  id: string
  isCenter: boolean
  x: number
  y: number
}

/**
 * A small, bounded, star-shaped subgraph renderer — hand-built rather
 * than a generic library, since the relationship model (typed edges
 * radiating from one center customer) is simple and fixed
 * (docs/FRONTEND_ARCHITECTURE.md §1). Node count is already bounded by
 * the backend (docs/TOOL_CONTRACTS.md's get_graph_neighbors
 * max_results), never paginated further here.
 */
export function CaseGraph({ graph, height = 420 }: { graph: CaseGraphResponse; height?: number }) {
  const [transform, setTransform] = useState({ scale: 1, x: 0, y: 0 })
  const [selectedEdge, setSelectedEdge] = useState<GraphVizEdge | null>(null)
  const dragState = useRef<{ startX: number; startY: number; originX: number; originY: number } | null>(null)

  const width = 720
  const radius = Math.min(width, height) * 0.36

  const positioned: Positioned[] = useMemo(() => {
    const center = graph.nodes.find((n) => n.is_center)
    const neighbors = graph.nodes.filter((n) => !n.is_center)
    const result: Positioned[] = []
    if (center) result.push({ id: center.customer_proxy_id, isCenter: true, x: width / 2, y: height / 2 })
    neighbors.forEach((n, i) => {
      const angle = (2 * Math.PI * i) / Math.max(neighbors.length, 1) - Math.PI / 2
      result.push({
        id: n.customer_proxy_id,
        isCenter: false,
        x: width / 2 + radius * Math.cos(angle),
        y: height / 2 + radius * Math.sin(angle),
      })
    })
    return result
  }, [graph.nodes, radius, height])

  const positionOf = (id: string) => positioned.find((p) => p.id === id)

  // When a neighbor shares more than one relationship type with the
  // center (multi_attribute_overlap — the highest-signal case), two
  // edges connect the exact same pair of nodes. Drawn as straight lines
  // they perfectly overlap and the later one hides the earlier one's
  // color entirely, defeating the point of typed edge colors. Each edge
  // in a >1 group is bowed by a small perpendicular offset instead, so
  // every relationship type stays visible (found during Phase 5B visual
  // validation on the strong-ring demo case).
  const edgePaths = useMemo(() => {
    const groups = new Map<string, GraphVizEdge[]>()
    graph.edges.forEach((edge) => {
      const key = [edge.source, edge.target].sort().join('|')
      groups.set(key, [...(groups.get(key) ?? []), edge])
    })
    const paths: { edge: GraphVizEdge; d: string }[] = []
    groups.forEach((group) => {
      group.forEach((edge, i) => {
        const source = positionOf(edge.source)
        const target = positionOf(edge.target)
        if (!source || !target) return
        const mx = (source.x + target.x) / 2
        const my = (source.y + target.y) / 2
        const dx = target.x - source.x
        const dy = target.y - source.y
        const len = Math.hypot(dx, dy) || 1
        const nx = -dy / len
        const ny = dx / len
        const offset = (i - (group.length - 1) / 2) * 14
        const cx = mx + nx * offset
        const cy = my + ny * offset
        paths.push({ edge, d: `M ${source.x} ${source.y} Q ${cx} ${cy} ${target.x} ${target.y}` })
      })
    })
    return paths
  }, [graph.edges, positioned])

  function handleWheel(e: WheelEvent<SVGSVGElement>) {
    e.preventDefault()
    const delta = e.deltaY > 0 ? 0.9 : 1.1
    setTransform((t) => ({ ...t, scale: Math.min(3, Math.max(0.5, t.scale * delta)) }))
  }

  function handleMouseDown(e: ReactMouseEvent<SVGSVGElement>) {
    dragState.current = { startX: e.clientX, startY: e.clientY, originX: transform.x, originY: transform.y }
  }
  function handleMouseMove(e: ReactMouseEvent<SVGSVGElement>) {
    if (!dragState.current) return
    const dx = e.clientX - dragState.current.startX
    const dy = e.clientY - dragState.current.startY
    setTransform((t) => ({ ...t, x: dragState.current!.originX + dx, y: dragState.current!.originY + dy }))
  }
  function handleMouseUp() {
    dragState.current = null
  }
  function resetView() {
    setTransform({ scale: 1, x: 0, y: 0 })
    setSelectedEdge(null)
  }

  if (graph.nodes.length === 0) {
    return (
      <div className="graph-empty">No shared infrastructure detected for this customer — nothing to visualize.</div>
    )
  }

  return (
    <div className="case-graph">
      <div className="graph-toolbar">
        <button type="button" className="btn btn-ghost btn-sm" onClick={resetView}>
          Reset view
        </button>
        <span className="graph-hint">scroll to zoom · drag to pan · click an edge for detail</span>
      </div>
      <svg
        width="100%"
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        role="img"
        aria-label="Case relationship graph"
      >
        <g transform={`translate(${transform.x} ${transform.y}) scale(${transform.scale})`}>
          {edgePaths.map(({ edge, d }, i) => {
            const isSelected = selectedEdge === edge
            return (
              <path
                key={i}
                d={d}
                fill="none"
                stroke={relationshipColor(edge.relationship_type)}
                strokeWidth={isSelected ? 3 : 1.75}
                opacity={isSelected ? 1 : 0.75}
                style={{ cursor: 'pointer' }}
                onClick={() => setSelectedEdge(edge)}
              >
                <title>
                  {relationshipTypeLabel(edge.relationship_type)}: {edge.shared_entity_value}
                </title>
              </path>
            )
          })}
          {positioned.map((node) => (
            <g key={node.id} transform={`translate(${node.x} ${node.y})`}>
              <circle r={node.isCenter ? 22 : 14} className={node.isCenter ? 'graph-node-center' : 'graph-node'} />
              <title>{node.id}</title>
            </g>
          ))}
        </g>
      </svg>
      <GraphLegend types={[...new Set(graph.edges.map((e) => e.relationship_type))]} colorFor={relationshipColor} />
      {selectedEdge && (
        <div className="graph-edge-detail">
          <strong>{relationshipTypeLabel(selectedEdge.relationship_type)}</strong> — shared value{' '}
          <code>{selectedEdge.shared_entity_value}</code>
          <div className="graph-edge-detail-endpoints">
            {selectedEdge.source} ↔ {selectedEdge.target}
          </div>
        </div>
      )}
    </div>
  )
}
