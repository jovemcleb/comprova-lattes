import { Route, Routes } from 'react-router'
import { AppShell } from './components/AppShell'
import { DashboardPage } from './pages/DashboardPage'
import { NewValidationPage } from './pages/NewValidationPage'
import { ValidationDetailPage } from './pages/ValidationDetailPage'
export default function App() {
  return <Routes><Route element={<AppShell />}><Route index element={<DashboardPage />} /><Route path="validacoes/nova" element={<NewValidationPage />} /><Route path="validacoes/:validationId" element={<ValidationDetailPage />} /><Route path="*" element={<p>Pagina nao encontrada.</p>} /></Route></Routes>
}
