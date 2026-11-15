import type { PackageRecord } from '../../lib/annotation/package'
import { FIELD_DEFS, type CaseAnnotation, type FieldKey } from '../../lib/annotation/draft'

const XML_FIELDS: Partial<Record<FieldKey, keyof PackageRecord>> = {
  holder_name: 'holder_name', issuer_institution: 'institution',
  issuer_acronym: 'institution_acronym', activity_title: 'title',
  event_name: 'event_name', participation_role_raw: 'participation_role',
  workload_hours: 'workload_hours', start_year: 'start_year', end_year: 'end_year',
}

export function ComparisonTable({ record, annotation, hasDocument }: {
  record: PackageRecord; annotation: CaseAnnotation; hasDocument: boolean
}) {
  return <div className="annot-comparison-scroll" tabIndex={0} role="region" aria-label="Comparação dos campos">
    <table className="annot-comparison-table">
      <caption>Compare as duas fontes. Valores diferentes não significam que sua transcrição está errada.</caption>
      <thead><tr><th scope="col">Campo</th><th scope="col">Sua transcrição do comprovante</th><th scope="col">Declarado no currículo</th></tr></thead>
      <tbody>{FIELD_DEFS.map(def => {
        const field = annotation.phase1.fields[def.key]
        const key = XML_FIELDS[def.key]
        const declared = key ? record[key] : null
        return <tr key={def.key}>
          <th scope="row">{def.label}</th>
          <td>{!hasDocument ? 'Sem comprovante' : field.state === 'present' ? field.value : field.state === 'illegible' ? 'Ilegível no comprovante' : field.state === 'absent' ? 'Ausente no comprovante' : 'Não preenchido'}</td>
          <td>{!key ? <span className="annot-note">Sem campo correspondente no XML{def.key === 'activity_year' ? '; confira os anos de início e conclusão, sem presumir equivalência.' : '.'}</span> : declared === null || declared === undefined || declared === '' ? 'Não informado no currículo' : String(declared)}</td>
        </tr>
      })}</tbody>
    </table>
  </div>
}
