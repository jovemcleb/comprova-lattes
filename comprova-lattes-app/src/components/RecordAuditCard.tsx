import type { ValidationDetail } from '../types/validation'
import { AuditData } from './AuditData'
import { FieldEvidenceTable } from './FieldEvidenceTable'
import { HumanReviewForm } from './HumanReviewForm'
import { StatusBadge } from './StatusBadge'
import { DocumentPanel } from './DocumentPanel'
export function RecordAuditCard({ validation, index }: { validation: ValidationDetail; index: number }) {
  const record = validation.records.find(item => item.record_index === index)!
  const verdict = record.automatic
  const curriculum = validation.parsed?.curriculum
  const sourceRecords = curriculum && typeof curriculum === 'object' && !Array.isArray(curriculum) ? curriculum.records : null
  const sourceRecord = Array.isArray(sourceRecords) ? sourceRecords[index] : null
  return <details className="panel record" open={record.review_required || undefined}><summary><span>Registro {index + 1} · {verdict.category} · {verdict.record_id}</span><StatusBadge status={verdict.status} />{record.review_required && <strong>Revisão pendente</strong>}</summary><AuditData title="Registro de origem M1 e proveniência XML" data={sourceRecord} /><h3>Decisão automática preservada</h3><p>{verdict.reason_code} · Documento: {verdict.matched_document_id ?? 'Sem associação'} · Escore: {verdict.association_score ?? 'Ausente'}</p>{verdict.diagnostics.map((message, i) => <p key={i}>{message}</p>)}<FieldEvidenceTable fields={verdict.field_evidences} /><h3>Candidatos de ambiguidade</h3>{!verdict.ambiguity_candidates.length && <p>Nenhum candidato ambíguo.</p>}{verdict.ambiguity_candidates.map(candidate => <details key={candidate.document_id}><summary>{candidate.document_id} · Escore {candidate.association_score}</summary><FieldEvidenceTable fields={candidate.field_evidences} /><AuditData title="Extração M3 do candidato" data={validation.extractions?.find(doc => doc.document_id === candidate.document_id)} /></details>)}<AuditData title="Extração M3 do documento associado" data={validation.extractions?.find(doc => doc.document_id === verdict.matched_document_id)} /><details><summary>Consultar documentos do lote para revisão</summary>{validation.input.documents.map(doc => <DocumentPanel key={doc.document_id} document={doc} />)}</details><HumanReviewForm validation={validation} index={index} /></details>
}
