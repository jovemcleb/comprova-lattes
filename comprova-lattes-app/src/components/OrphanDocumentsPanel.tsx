import type { ValidationDetail } from '../types/validation'
export function OrphanDocumentsPanel({ validation }: { validation: ValidationDetail }) {
  const orphans = validation.automatic_result?.orphan_documents ?? []
  return <section className="panel"><h2>Documentos não associados</h2><p>DOCUMENTO_NAO_ASSOCIADO · Órfãos reportados separadamente, fora da matriz 3 × 3 dos registros.</p>{!orphans.length && <p>Nenhum órfão reportado.</p>}{orphans.map(doc => <p key={doc.document_id}><strong>{doc.document_id}</strong> · {validation.input.documents.find(input => input.document_id === doc.document_id)?.filename} · Melhor candidato: {doc.best_candidate_record_id ?? 'nenhum'} · Escore: {doc.best_association_score ?? 'ausente'}</p>)}</section>
}
