import { useState } from 'react'
import { decodeXml, type PackageCase, type PackageRecord } from '../../lib/annotation/package'
import {
  ASSOCIATIONS,
  FIELD_DEFS,
  FIELD_LABEL,
  FIELD_STATES,
  REASONS,
  VERDICTS,
  emptyPhase1,
  emptyPhase2,
  reasonAllows,
  validatePhase2,
  type Association,
  type CaseAnnotation,
  type FieldKey,
  type Phase2,
  type ReasonCode,
  type Verdict,
} from '../../lib/annotation/draft'
import type { CaseUpdater } from './DocumentPhase'
import { DocumentViewer } from './DocumentViewer'
import { ErrorSummary } from './ErrorSummary'
import { RadioGroup } from './RadioGroup'

const RECORD_LABELS: [keyof PackageRecord, string][] = [
  ['category', 'Categoria'],
  ['holder_name', 'Titular'],
  ['institution', 'Instituição'],
  ['institution_acronym', 'Sigla'],
  ['title', 'Título / atividade'],
  ['event_name', 'Evento'],
  ['participation_role', 'Papel'],
  ['participation_type_raw', 'Tipo de participação'],
  ['participation_form_raw', 'Forma de participação'],
  ['nature_raw', 'Natureza'],
  ['subtype', 'Subtipo'],
  ['start_year', 'Ano de início'],
  ['end_year', 'Ano de conclusão'],
  ['workload_hours', 'Carga horária'],
  ['status', 'Situação'],
  ['city', 'Cidade'],
  ['location', 'Local'],
  ['validation_code', 'Código de validação'],
  ['record_id', 'Identificador do registro'],
  ['sequence', 'Sequência'],
]

const FIELD_STATE_LABEL = Object.fromEntries(FIELD_STATES.map(item => [item.value, item.label]))
const ASSOCIATION_LABEL = Object.fromEntries(ASSOCIATIONS.map(item => [item.value, item.label]))
const VERDICT_LABEL = Object.fromEntries(VERDICTS.map(item => [item.value, item.label]))

interface ComparisonPhaseProps {
  pkgCase: PackageCase
  annotation: CaseAnnotation
  onChange: CaseUpdater
}

/** Fase 2: XML legível ao lado do comprovante; a transcrição da fase 1 está travada. */
export function ComparisonPhase({ pkgCase, annotation, onChange }: ComparisonPhaseProps) {
  const [problems, setProblems] = useState<string[]>([])
  const [confirmReopen, setConfirmReopen] = useState(false)
  const { document, record } = pkgCase
  const hasDocument = document !== null
  const phase = annotation.phase2 ?? emptyPhase2()
  const locked = phase.status === 'saved'

  function edit(patch: Partial<Phase2>) {
    setProblems([])
    onChange(current => ({ ...current, phase2: { ...(current.phase2 ?? emptyPhase2()), ...patch } }))
  }

  function setVerdict(verdict: Verdict) {
    const keep = phase.reason_code && reasonAllows(phase.reason_code, verdict)
    edit({ verdict, reason_code: keep ? phase.reason_code : null })
  }

  function toggleBasis(key: FieldKey, checked: boolean) {
    const rest = phase.basis_fields.filter(item => item !== key)
    edit({ basis_fields: checked ? [...rest, key] : rest })
  }

  function save() {
    const found = validatePhase2(phase, hasDocument)
    setProblems(found)
    if (found.length) return
    const stamp = new Date().toISOString()
    onChange(current => ({ ...current, phase2: { ...(current.phase2 ?? emptyPhase2()), status: 'saved', saved_at: stamp } }))
  }

  function reopenPhase1() {
    setConfirmReopen(false)
    onChange(current => ({
      ...current,
      phase1: { ...emptyPhase1(), fields: current.phase1.fields, absence_acknowledged: current.phase1.absence_acknowledged },
      phase2: null,
      phase1_reopen_count: current.phase1_reopen_count + 1,
    }))
  }

  const reasons = REASONS.filter(item => phase.verdict !== null && reasonAllows(item.code, phase.verdict))

  return (
    <div className={document ? 'annot-split' : undefined}>
      {document && <DocumentViewer document={document} caseId={pkgCase.case_id} />}
      <div>
        <section aria-labelledby={`xml-${pkgCase.case_id}`}>
          <h3 id={`xml-${pkgCase.case_id}`}>Fase 2 · Registro curricular (XML)</h3>
          <dl className="annot-record">
            {RECORD_LABELS.filter(([key]) => record[key] !== null).map(([key, label]) => (
              <div key={key} style={{ display: 'contents' }}>
                <dt>{label}</dt>
                <dd>{String(record[key])}</dd>
              </div>
            ))}
          </dl>
          <details>
            <summary>XML original</summary>
            <pre tabIndex={0}>{decodeXml(pkgCase)}</pre>
          </details>
        </section>

        <section className="annot-locked" aria-labelledby={`saved1-${pkgCase.case_id}`}>
          <h3 id={`saved1-${pkgCase.case_id}`}>Sua transcrição (fase 1, travada)</h3>
          {hasDocument ? (
            <dl className="annot-record">
              {FIELD_DEFS.map(def => {
                const field = annotation.phase1.fields[def.key]
                return (
                  <div key={def.key} style={{ display: 'contents' }}>
                    <dt>{def.label}</dt>
                    <dd>{field.state === 'present' ? field.value : FIELD_STATE_LABEL[field.state ?? 'absent']}</dd>
                  </div>
                )
              })}
            </dl>
          ) : (
            <p>Ausência de documento confirmada; sem transcrição.</p>
          )}
          {confirmReopen ? (
            <div className="attention">
              <p>Reabrir a fase 1 depois de ver o XML apaga a fase 2 deste caso e fica registrado ({annotation.phase1_reopen_count + 1}ª reabertura) no arquivo exportado. Não copie valores do XML para o documento.</p>
              <button type="button" onClick={reopenPhase1}>Reabrir fase 1 e apagar fase 2</button>
              <button type="button" className="secondary" onClick={() => setConfirmReopen(false)}>Cancelar</button>
            </div>
          ) : (
            <button type="button" className="secondary" onClick={() => setConfirmReopen(true)}>Reabrir fase 1…</button>
          )}
        </section>

        <section aria-labelledby={`judge-${pkgCase.case_id}`}>
          <h3 id={`judge-${pkgCase.case_id}`}>Associação, classe e motivo</h3>
          <fieldset disabled={locked}>
            <RadioGroup<Association>
              legend="O comprovante se refere a este registro curricular?"
              name={`${pkgCase.case_id}-association`}
              options={ASSOCIATIONS}
              value={phase.association}
              disabledValues={hasDocument ? [] : ['sim']}
              hint={hasDocument ? undefined : 'Sem documento neste caso: "sim" está indisponível.'}
              onChange={association => edit({ association })}
            />
            <RadioGroup<Verdict>
              legend="Classe do registro"
              name={`${pkgCase.case_id}-verdict`}
              options={VERDICTS}
              value={phase.verdict}
              hint="Sem evidência suficiente, a classe é Inconclusivo. A classe não é preenchida nem sugerida pela interface."
              onChange={setVerdict}
            />
            <label>
              Motivo objetivo
              <select
                value={phase.reason_code ?? ''}
                disabled={phase.verdict === null}
                onChange={event => edit({ reason_code: (event.target.value || null) as ReasonCode | null })}
              >
                <option value="">{phase.verdict === null ? 'Escolha a classe primeiro' : 'Selecione…'}</option>
                {reasons.map(item => (
                  <option key={item.code} value={item.code}>{item.label}</option>
                ))}
              </select>
            </label>
            <fieldset>
              <legend>Campos que fundamentam o motivo (opcional, obrigatório para diferença factual)</legend>
              <div className="annot-inline">
                {FIELD_DEFS.map(def => (
                  <label className="checkbox" key={def.key}>
                    <input
                      type="checkbox"
                      checked={phase.basis_fields.includes(def.key)}
                      onChange={event => toggleBasis(def.key, event.target.checked)}
                    />
                    {FIELD_LABEL[def.key]}
                  </label>
                ))}
              </div>
            </fieldset>
            <label>
              Nota contextual (cite o trecho documental quando a análise for contextual)
              <textarea rows={4} maxLength={2000} value={phase.note} onChange={event => edit({ note: event.target.value })} />
            </label>
          </fieldset>
          <ErrorSummary problems={problems} />
          <div className="annot-actions">
            {locked ? (
              <>
                <p role="status">
                  Caso concluído: {ASSOCIATION_LABEL[phase.association ?? 'incerto']} · {VERDICT_LABEL[phase.verdict ?? 'INCONCLUSIVO']}.
                </p>
                <button type="button" className="secondary" onClick={() => edit({ status: 'in_progress', saved_at: null })}>Editar fase 2</button>
              </>
            ) : (
              <button type="button" onClick={save}>Salvar fase 2 e concluir caso</button>
            )}
          </div>
        </section>
      </div>
    </div>
  )
}
