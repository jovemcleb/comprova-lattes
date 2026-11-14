import { useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { useHealth, useValidationsList } from '../hooks/useValidations'
import { ErrorNotice } from '../components/AuditData'
import { StatusBadge } from '../components/StatusBadge'
export function DashboardPage() {
  const [offset, setOffset] = useState(0)
  const [id, setId] = useState('')
  const list = useValidationsList(offset)
  const health = useHealth()
  const navigate = useNavigate()
  return <><div className="page-heading"><div><p className="eyebrow">Conferência acadêmica</p><h1>Suas validações</h1><p>Do currículo à evidência, com cada decisão à vista.</p></div><Link className="button" to="/validacoes/nova">Nova validação</Link></div>
    {health.data && <p className="service-info">API {health.data.version} · Ambiente {health.data.environment} · Modelo de extração {health.data.gemini_model}. Saúde da API não comprova conexão com worker, banco ou Gemini.</p>}
    <form className="lookup" onSubmit={event => { event.preventDefault(); if (id.trim()) void navigate(`/validacoes/${encodeURIComponent(id.trim())}`) }}><label>Consultar pelo ID<input required value={id} onChange={event => setId(event.target.value)} placeholder="ID da validação" /></label><button>Abrir</button></form>
    <section className="panel"><h2>Histórico de lotes</h2><p>Do mais recente ao mais antigo.</p>{list.isPending && <p role="status">Carregando validações…</p>}<ErrorNotice error={list.error} />{list.isError && <button onClick={() => void list.refetch()}>Tentar novamente</button>}{list.data?.length === 0 && <p>Nenhuma validação nesta página. Crie um lote ou volte à página anterior.</p>}
      {list.data && list.data.length > 0 && <div className="table-scroll"><table><thead><tr><th>Validação</th><th>Criação</th><th>Estado</th><th>Erro</th></tr></thead><tbody>{list.data.map(item => <tr key={item.id}><td><Link to={`/validacoes/${item.id}`}>{item.id}</Link></td><td>{new Date(item.created_at).toLocaleString('pt-BR')}</td><td><StatusBadge status={item.status} /></td><td>{item.error_code ?? '—'}</td></tr>)}</tbody></table></div>}
      <div className="pagination"><button className="secondary" disabled={!offset || list.isFetching} onClick={() => setOffset(Math.max(0, offset - 20))}>Anterior</button><span>Página {offset / 20 + 1}</span><button className="secondary" disabled={list.isFetching || !list.data || list.data.length < 20} onClick={() => setOffset(offset + 20)}>Próxima</button></div></section></>
}
