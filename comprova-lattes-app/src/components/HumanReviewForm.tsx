import { useState } from 'react'
import type { MatchStatus, ValidationDetail } from '../types/validation'
import { useSubmitHumanReview } from '../hooks/useValidations'
import { ErrorNotice } from './AuditData'
import { StatusBadge } from './StatusBadge'

export function HumanReviewForm({ validation, index }: { validation: ValidationDetail; index: number }) {
  const record = validation.records.find(item => item.record_index === index)!
  const latest = record.human_review
  const [open, setOpen] = useState(record.review_required)
  const [matched, setMatched] = useState((latest ?? record.automatic).matched_document_id ?? '')
  const [rejected, setRejected] = useState<string[]>(latest?.rejected_document_ids ?? [])
  const [reviewer, setReviewer] = useState('')
  const [justification, setJustification] = useState('')
  const [status, setStatus] = useState<MatchStatus>(latest?.status ?? record.automatic.status)
  const [saved, setSaved] = useState(false)
  const mutation = useSubmitHumanReview(validation.id, index)
  const documents = validation.input.documents
  return <section className="review"><h3>Revisão humana · AD-013</h3>{record.review_required && <p className="attention">Encaminhado para revisão: resultado INCONCLUSIVO.</p>}{latest && <p>Último parecer: <StatusBadge status={latest.status} /> · {latest.reviewer}</p>}
    {!open && <button type="button" onClick={() => { const persisted = latest ?? record.automatic; setStatus(persisted.status); setMatched(persisted.matched_document_id ?? ''); setRejected(latest?.rejected_document_ids ?? []); setOpen(true); setSaved(false) }}>Solicitar {latest ? 'nova revisão' : 'revisão deste resultado'}</button>}
    {open && <form onSubmit={async event => { event.preventDefault(); if (!reviewer.trim() || !justification.trim()) return; setSaved(false); try { await mutation.mutateAsync({ reviewer: reviewer.trim(), justification: justification.trim(), status, matched_document_id: matched || null, rejected_document_ids: rejected }); setSaved(true); setOpen(false); setJustification('') } catch { /* O erro é exibido abaixo e os campos são preservados. */ } }}>
      <p>Identidade declarada, sem autenticação. Cada envio acrescenta um parecer e preserva a decisão automática.</p><fieldset disabled={mutation.isPending}><div className="grid gap-4 md:grid-cols-2"><label>Revisor obrigatório<input required value={reviewer} onChange={event => setReviewer(event.target.value)} /></label><label>Parecer<select value={status} onChange={event => setStatus(event.target.value as MatchStatus)}>{['VALIDADO', 'DIVERGENTE', 'INCONCLUSIVO'].map(value => <option key={value}>{value}</option>)}</select></label></div>
      <label>Documento associado (qualquer documento do lote)<select value={matched} onChange={event => { setMatched(event.target.value); setRejected(rejected.filter(id => id !== event.target.value)) }}><option value="">Sem documento associado</option>{documents.map(doc => <option key={doc.document_id} value={doc.document_id}>{doc.document_id} · {doc.filename}</option>)}</select></label>
      <fieldset><legend>Documentos rejeitados</legend>{!documents.length && <p>Nenhum documento no lote.</p>}{documents.map(doc => <label className="checkbox" key={doc.document_id}><input type="checkbox" disabled={matched === doc.document_id} checked={rejected.includes(doc.document_id)} onChange={event => setRejected(event.target.checked ? [...rejected, doc.document_id] : rejected.filter(id => id !== doc.document_id))} />{doc.document_id} · {doc.filename}</label>)}</fieldset>
      <label>Justificativa obrigatória<textarea required rows={3} value={justification} onChange={event => setJustification(event.target.value)} /></label><button disabled={!reviewer.trim() || !justification.trim()}>{mutation.isPending ? 'Salvando…' : 'Registrar parecer'}</button><button type="button" className="secondary" onClick={() => setOpen(false)}>Cancelar</button></fieldset>
    </form>}<ErrorNotice error={mutation.error} />{saved && <p role="status">Parecer registrado. Histórico e sumário atualizados.</p>}
    <h4>Histórico de revisões</h4>{validation.reviews.filter(review => review.record_index === index).map(review => <article className="history" key={review.id}><StatusBadge status={review.status} /><p>{review.reviewer} · {new Date(review.reviewed_at).toLocaleString('pt-BR')}</p><p>{review.justification}</p><small>Associado: {review.matched_document_id ?? 'nenhum'} · Rejeitados: {review.rejected_document_ids.join(', ') || 'nenhum'}</small></article>)}{!latest && <p>Nenhum parecer registrado.</p>}
  </section>
}
