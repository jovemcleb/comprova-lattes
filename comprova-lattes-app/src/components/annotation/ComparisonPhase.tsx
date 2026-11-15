import { useState } from 'react'
import { decodeXml, type PackageCase, type PackageRecord } from '../../lib/annotation/package'
import {
  ASSOCIATIONS,
  FIELD_DEFS,
  FIELD_LABEL,
  REASONS,
  VERDICTS,
  emptyPhase1,
  emptyPhase2,
  isCaseOcrAssisted,
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
import { ComparisonTable } from './ComparisonTable'
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
  const ocr = annotation.ocr_assistance
  const ocrUsed = isCaseOcrAssisted(ocr)

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
          <h3 id={`xml-${pkgCase.case_id}`}>2. Compare com o que foi declarado no currículo</h3>
          <p>O comprovante e o currículo são fontes diferentes e podem discordar. Mantenha sua transcrição fiel ao documento; nesta etapa você avalia a relação entre as fontes.</p>
          <ComparisonTable record={record} annotation={annotation} hasDocument={hasDocument} />
          <details className="annot-technical">
            <summary>Detalhes técnicos e XML original</summary>
            <dl className="annot-record">
              {RECORD_LABELS.filter(([key]) => record[key] !== null).map(([key, label]) => (
                <div key={key} style={{ display: 'contents' }}><dt>{label}</dt><dd>{String(record[key])}</dd></div>
              ))}
            </dl>
            <pre tabIndex={0}>{decodeXml(pkgCase)}</pre>
            {ocrUsed && <p className="annot-note">Auxílio OCR consultado: {ocr.requested_count} vez(es); {ocr.provider}; {ocr.tesseract_version}; DPI {ocr.params?.dpi ?? 'não registrado'}. Cópias observadas: {ocr.observable_copied_fields.map(k => FIELD_LABEL[k]).join(', ') || 'nenhuma'}. O registro detalhado permanece no JSON.</p>}
          </details>
        </section>

        <section className="annot-transcription-controls" aria-label="Corrigir sua transcrição">
          <p className="annot-note">Sua transcrição está salva. Se notar um erro de leitura, reabra a etapa anterior. Não troque o valor do comprovante apenas para coincidir com o currículo.</p>
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
          <h3 id={`judge-${pkgCase.case_id}`}>3. Registre sua conclusão</h3>
          <fieldset disabled={locked}>
            <RadioGroup<Association>
              legend="Este comprovante corresponde à atividade declarada?"
              name={`${pkgCase.case_id}-association`}
              options={ASSOCIATIONS}
              value={phase.association}
              disabledValues={hasDocument ? [] : ['sim']}
              hint={hasDocument ? 'Você pode reconhecer a mesma atividade e ainda encontrar diferenças nos dados. Associação não significa que todas as informações conferem.' : 'Sem documento neste caso: "sim" está indisponível.'}
              onChange={association => edit({ association })}
            />
            <RadioGroup<Verdict>
              legend="Como você avalia as informações comparadas?"
              name={`${pkgCase.case_id}-verdict`}
              options={VERDICTS}
              value={phase.verdict}
              hint="Validado: informações compatíveis conforme o guia. Divergente: diferença factual comprovada. Inconclusivo: evidência insuficiente ou ambígua. Você escolhe; a interface não calcula a resposta."
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
              <button type="button" onClick={save}>Salvar avaliação e concluir caso</button>
            )}
          </div>
        </section>
      </div>
    </div>
  )
}
