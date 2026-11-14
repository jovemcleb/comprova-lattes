import type { FieldEvidence } from '../types/validation'
import { StatusBadge } from './StatusBadge'
const value = (item: string | number | null) => item === null ? 'Ausente' : String(item)
export function FieldEvidenceTable({ fields }: { fields: FieldEvidence[] }) {
  if (!fields.length) return <p>Sem evidências por campo para esta associação.</p>
  return <div className="table-scroll"><table><caption>Evidências por campo · valores e regras preservados</caption><thead><tr><th>Campo / resultado</th><th>Lattes (bruto / normalizado)</th><th>Documento (bruto / normalizado)</th><th>Regra e evidência</th></tr></thead><tbody>{fields.map((f, index) => <tr key={`${f.field_name}-${index}`}><th>{f.field_name}<br /><StatusBadge status={f.outcome} /></th><td>{value(f.lattes_raw)}<small>{value(f.lattes_normalized)}</small></td><td>{value(f.document_raw)}<small>{value(f.document_normalized)}</small></td><td><strong>{f.rule_applied}</strong><p>{f.justification_pt}</p><small>Similaridade: {value(f.similarity_score)} · Diferença: {value(f.numeric_difference)}</small></td></tr>)}</tbody></table></div>
}
