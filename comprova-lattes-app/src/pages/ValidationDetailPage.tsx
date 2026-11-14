import { useState } from 'react'
import { useParams } from 'react-router'
import { useValidationDetail } from '../hooks/useValidations'
import { AuditData, ErrorNotice } from '../components/AuditData'
import { StatusBadge } from '../components/StatusBadge'
import { SummaryComparison } from '../components/SummaryComparison'
import { RecordAuditCard } from '../components/RecordAuditCard'
import { OrphanDocumentsPanel } from '../components/OrphanDocumentsPanel'
import { ParserDiagnosticsPanel } from '../components/ParserDiagnosticsPanel'
export function ValidationDetailPage() {
  const { validationId = '' } = useParams()
  const query = useValidationDetail(validationId)
  const [filter, setFilter] = useState('all')
  if (query.isPending) return <p role="status">Carregando auditoria…</p>
  if (!query.data) return <><ErrorNotice error={query.error} /><button onClick={() => void query.refetch()}>Tentar novamente</button></>
  const data = query.data
  const running = ['PENDING', 'PROCESSING'].includes(data.status)
  const records = data.records.filter(record => filter === 'all' || (filter === 'pending' ? record.review_required : record.automatic.status === filter))
  return <><div className="page-heading"><div><p className="eyebrow">Auditoria do lote</p><h1>Validação</h1><p className="break-all">{data.id} · {new Date(data.created_at).toLocaleString('pt-BR')}</p></div><StatusBadge status={data.status} /><button className="secondary" disabled={query.isFetching} onClick={() => void query.refetch()}>Atualizar</button></div><ErrorNotice error={query.error} />
    {running && <p role="status" className="attention">{data.status === 'PENDING' ? 'Aguardando worker.' : 'Processando M1 → M3 → M2.'} Consulta automática a cada 2 segundos; a API não informa progresso por etapa.</p>}{data.error_code && <p role="alert" className="error">Falha: {data.error_code}. Este lote não será reenviado automaticamente.</p>}
    <SummaryComparison validation={data} /><ParserDiagnosticsPanel validation={data} />
    <section><h2>M3 · Extração dos documentos</h2><p>Entidades e metadados extraídos. Confiança e categoria sugerida pelo LLM não decidem a classificação.</p>{!data.extractions?.length && <p>Nenhuma extração disponível.</p>}{data.extractions?.map(doc => <div className="panel" key={doc.document_id}><h3>{doc.document_id} · {data.input.documents.find(input => input.document_id === doc.document_id)?.filename}</h3><StatusBadge status={doc.extraction_status} /><AuditData title="Entidades, falhas e metadados completos" data={doc} /></div>)}</section>
    <section><h2>M2 · Registros e revisão</h2><label>Filtrar registros (classe automática)<select value={filter} onChange={event => setFilter(event.target.value)}><option value="all">Todos</option><option value="pending">Revisão pendente</option><option>VALIDADO</option><option>DIVERGENTE</option><option>INCONCLUSIVO</option></select></label><p>{records.length} registro(s) exibido(s) de {data.records.length}.</p>{records.map(record => <RecordAuditCard key={`${data.id}-${record.record_index}`} validation={data} index={record.record_index} />)}{!records.length && <p>Nenhum registro neste filtro.</p>}</section>
    <OrphanDocumentsPanel validation={data} /><AuditData title="Associações automáticas completas" data={data.automatic_result?.association_pairs} /><AuditData title="Configuração do matcher utilizada neste lote" data={data.input.matcher_config} />
  </>
}
