import { Link, useNavigate, useParams } from 'react-router-dom'
import { PageShell } from '../components/layout/PageShell'
import { Card } from '../components/common/Card'
import { Skeleton } from '../components/common/Skeleton'
import { StatePanel } from '../components/common/StatePanel'
import { XCircleIcon } from '../components/common/Icons'
import { CaseGraph } from '../components/graph/CaseGraph'
import { useCase, useCaseGraph } from '../hooks/useCases'

export function GraphExplorerPage() {
  const { caseId } = useParams<{ caseId: string }>()
  const navigate = useNavigate()
  const caseQuery = useCase(caseId)
  const graphQuery = useCaseGraph(caseId)

  return (
    <PageShell
      title={`Graph Explorer — ${caseId}`}
      subtitle={caseQuery.data?.graph_evidence ? caseQuery.data.graph_evidence.narrative : undefined}
      action={
        <Link to={`/cases/${caseId}`} className="btn btn-ghost btn-sm">
          ← Back to case
        </Link>
      }
    >
      <Card>
        {graphQuery.isLoading ? (
          <Skeleton height={520} />
        ) : graphQuery.isError ? (
          <StatePanel
            icon={<XCircleIcon />}
            variant="error"
            title="Could not load graph"
            actionLabel="Back to Case Queue"
            onAction={() => navigate('/cases')}
          />
        ) : graphQuery.data ? (
          <CaseGraph graph={graphQuery.data} height={560} />
        ) : null}
      </Card>
    </PageShell>
  )
}
