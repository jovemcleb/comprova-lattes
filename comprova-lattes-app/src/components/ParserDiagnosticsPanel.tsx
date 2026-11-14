import type { ValidationDetail } from '../types/validation'
import { AuditData } from './AuditData'
export function ParserDiagnosticsPanel({ validation }: { validation: ValidationDetail }) {
  return <section className="panel"><h2>M1 · Parser e fonte curricular</h2><p>Encoding declarado: {validation.parsed?.declared_encoding ?? 'Não disponível'}</p><AuditData title="Diagnósticos do parser" data={validation.parsed?.diagnostics} /><AuditData title="Variantes não verificadas" data={validation.parsed?.unverified_variants} /><AuditData title="Elementos não reconhecidos" data={validation.parsed?.unrecognized_elements} /><AuditData title="Currículo completo · registros M1" data={validation.parsed?.curriculum} /></section>
}
