import { NavLink, Outlet } from 'react-router'
import { useHealth } from '../hooks/useValidations'
export function AppShell() {
  const health = useHealth()
  return <><a className="skip-link" href="#content">Ir para conteúdo</a><header><div className="shell header-inner"><NavLink to="/" className="brand">Comprova <strong>Lattes</strong></NavLink><nav aria-label="Principal"><NavLink to="/" end>Validações</NavLink><NavLink to="/validacoes/nova">Nova validação</NavLink><NavLink to="/revisao-experimental">Revisão experimental</NavLink></nav><span role="status" className="health">{health.isPending ? 'Conectando…' : health.isError ? 'API indisponível' : `API ${health.data.status} · ${health.data.environment}`}</span></div></header><main id="content" className="shell py-10"><Outlet /></main><footer className="shell">LLM extrai entidades. O motor determinístico decide. A revisão humana permanece rastreável.</footer></>
}
