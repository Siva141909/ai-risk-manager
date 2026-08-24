import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { TopNav } from '../components/layout/TopNav'
import { shouldRetryQuery } from '../services/apiClient'
import { RiskOverviewPage } from '../pages/RiskOverviewPage'
import { CaseQueuePage } from '../pages/CaseQueuePage'
import { CaseInvestigationPage } from '../pages/CaseInvestigationPage'
import { GraphExplorerPage } from '../pages/GraphExplorerPage'
import { InvestigationReportPage } from '../pages/InvestigationReportPage'
import { DemoPage } from '../pages/DemoPage'
import '../styles/tokens.css'
import '../pages/pages.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: shouldRetryQuery,
      refetchOnWindowFocus: false,
    },
  },
})

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <TopNav />
        <Routes>
          <Route path="/" element={<RiskOverviewPage />} />
          <Route path="/cases" element={<CaseQueuePage />} />
          <Route path="/cases/:caseId" element={<CaseInvestigationPage />} />
          <Route path="/cases/:caseId/graph" element={<GraphExplorerPage />} />
          <Route path="/cases/:caseId/report" element={<InvestigationReportPage />} />
          <Route path="/demo" element={<DemoPage />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
