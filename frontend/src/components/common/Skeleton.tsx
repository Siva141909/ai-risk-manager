import './common.css'

export function Skeleton({ width = '100%', height = 16 }: { width?: string | number; height?: string | number }) {
  return <div className="skeleton" style={{ width, height }} />
}

export function TableSkeleton({ rows = 5, cols = 6 }: { rows?: number; cols?: number }) {
  return (
    <table className="data-table">
      <tbody>
        {Array.from({ length: rows }).map((_, r) => (
          <tr key={r}>
            {Array.from({ length: cols }).map((_, c) => (
              <td key={c}>
                <Skeleton height={14} />
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  )
}
