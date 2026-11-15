import { useState } from 'react'
import type { PackageCase } from '../../lib/annotation/package'
import {
  emptyPhase2,
  FIELD_DEFS,
  FIELD_STATES,
  recordOcrCopyField,
  recordOcrCopyRawText,
  rejectOcrFieldSuggestion,
  validatePhase1,
  type CaseAnnotation,
  type FieldKey,
  type FieldState,
  type ReviewMode,
} from '../../lib/annotation/draft'
import type { VerifiedOcrResponse } from '../../lib/annotation/ocr'
import { DocumentViewer } from './DocumentViewer'
import { ErrorSummary } from './ErrorSummary'
import { OcrAssistPanel } from './OcrAssistPanel'
import { RadioGroup } from './RadioGroup'


const FIELD_HELP: Record<FieldKey, string> = {
  holder_name: 'Nome da pessoa a quem o comprovante foi emitido.',
  issuer_institution: 'Nome da instituição emissora, como aparece no documento.',
  issuer_acronym: 'Somente a sigla impressa no comprovante. Não crie uma sigla a partir do nome.',
  issuer_name_acronym_evidence: 'Copie o trecho que apresenta juntos o nome da instituição e a sigla. Se não houver esse trecho, marque ausente.',
  activity_title: 'Procure a atividade específica (por exemplo, a linha “Atividade”). O cabeçalho “Declaração de participação” ou “Certificado” é o tipo do documento, não o título da atividade.',
  event_name: 'Nome do evento em que a atividade aconteceu. É diferente do título da atividade.',
  participation_role_raw: 'Papel escrito no comprovante, sem reinterpretar ou completar.',
  workload_hours: 'Quantidade de horas declarada, sem converter datas em carga horária.',
  start_year: 'Ano explicitamente indicado como início. Não deduza pelo ano de conclusão.',
  end_year: 'Ano explicitamente indicado como conclusão ou término.',
  activity_year: 'Ano explicitamente atribuído à atividade ou ao evento. Não preencha automaticamente com os outros anos.',
}

export type CaseUpdater = (update: (annotation: CaseAnnotation) => CaseAnnotation) => void

interface DocumentPhaseProps {
  pkgCase: PackageCase
  annotation: CaseAnnotation
  reviewMode: ReviewMode
  onChange: CaseUpdater
  onOptInAndRead: (caseId: string) => void
  onOcrSuccess: (caseId: string, response: VerifiedOcrResponse) => void
  onOcrFailure: (caseId: string, errorMessage: string) => void
}

/** Fase 1: transcrição do documento em branco, com auxílio OCR opcional explícito (sem preenchimento automático nem XML/gabarito). */
export function DocumentPhase({
  pkgCase,
  annotation,
  reviewMode,
  onChange,
  onOptInAndRead,
  onOcrSuccess,
  onOcrFailure,
}: DocumentPhaseProps) {
  const [problems, setProblems] = useState<string[]>([])
  const { document } = pkgCase
  const phase = annotation.phase1

  function edit(update: (fields: typeof phase.fields) => typeof phase.fields) {
    setProblems([])
    onChange(current => ({ ...current, phase1: { ...current.phase1, fields: update(current.phase1.fields) } }))
  }

  function setState(key: FieldKey, state: FieldState) {
    edit(fields => ({ ...fields, [key]: { state, value: state === 'present' ? fields[key].value : '' } }))
  }

  function setValue(key: FieldKey, value: string) {
    edit(fields => ({ ...fields, [key]: { ...fields[key], value } }))
  }

  function handleCopyRawText() {
    onChange(current => recordOcrCopyRawText(current))
  }

  function handleCopyField(fieldKey: FieldKey, applyToField: boolean) {
    setProblems([])
    onChange(current => recordOcrCopyField(current, fieldKey, applyToField))
  }

  function handleRejectOcrSuggestion(fieldKey: FieldKey) {
    setProblems([])
    onChange(current => rejectOcrFieldSuggestion(current, fieldKey))
  }

  function save() {
    const found = validatePhase1(phase, document !== null)
    setProblems(found)
    if (found.length) return
    const stamp = new Date().toISOString()
    onChange(current => ({
      ...current,
      phase1: { ...current.phase1, status: 'saved', saved_at: stamp },
      phase2: current.phase2 ?? emptyPhase2(),
    }))
  }

  return (
    <div className={document ? 'annot-split' : undefined}>
      {document && <DocumentViewer document={document} caseId={pkgCase.case_id} />}
      <section aria-labelledby={`phase1-${pkgCase.case_id}`}>
        <h3 id={`phase1-${pkgCase.case_id}`}>1. O que está no comprovante?</h3>
        {document ? (
          <>
            <p>
              Leia o comprovante e registre somente o que ele informa, preservando acentos, maiúsculas, minúsculas e números. O currículo aparece apenas na próxima etapa; não é necessário fazer os valores coincidirem.
              Para cada campo, marque <strong>presente</strong> (com o valor literal), <strong>ausente</strong> (não consta) ou{' '}
              <strong>ilegível</strong> (consta, mas não dá para ler). Ausente e ilegível são estados distintos.
            </p>
            <OcrAssistPanel
              pkgCase={pkgCase}
              annotation={annotation}
              reviewMode={reviewMode}
              onOptInAndRead={onOptInAndRead}
              onOcrSuccess={onOcrSuccess}
              onOcrFailure={onOcrFailure}
              onCopyRawText={handleCopyRawText}
              onCopyField={handleCopyField}
            />
          </>
        ) : (
          <div className="attention">
            <p>
              <strong>Este caso não possui documento.</strong> A transcrição e o OCR estão desativados e nada é preenchido ou classificado
              automaticamente. Confirme a ausência para liberar a fase 2.
            </p>
            <label className="checkbox">
              <input
                type="checkbox"
                checked={phase.absence_acknowledged}
                onChange={event => {
                  setProblems([])
                  const checked = event.target.checked
                  onChange(current => ({ ...current, phase1: { ...current.phase1, absence_acknowledged: checked } }))
                }}
              />
              Confirmo que não há documento neste caso
            </label>
          </div>
        )}
        {FIELD_DEFS.map(def => {
          const field = phase.fields[def.key]
          const name = `${pkgCase.case_id}-${def.key}`
          const usedOcr = annotation.ocr_assistance.observable_copied_fields.includes(def.key)
          return (
            <div className="annot-field" key={def.key}>
              <RadioGroup
                legend={def.label}
                name={name}
                options={FIELD_STATES}
                value={field.state}
                disabled={document === null}
                hint={FIELD_HELP[def.key]}
                onChange={state => setState(def.key, state)}
              />
              <label>
                Valor transcrito
                <input
                  value={field.value}
                  disabled={document === null || field.state !== 'present'}
                  inputMode={def.kind === 'year' ? 'numeric' : undefined}
                  maxLength={500}
                  onChange={event => setValue(def.key, event.target.value)}
                />
              </label>
              {usedOcr && (
                <div className="annot-ocr-field-audit">
                  <span className="annot-note">
                    Sugestão OCR consultada/copiada neste campo — confira visualmente no comprovante. O registro de consulta permanece auditável no JSON.
                  </span>
                  {(field.state !== null || field.value !== '') && (
                    <button
                      type="button"
                      className="secondary"
                      onClick={() => handleRejectOcrSuggestion(def.key)}
                    >
                      Rejeitar / limpar valor deste campo
                    </button>
                  )}
                </div>
              )}
            </div>
          )
        })}
        <ErrorSummary problems={problems} />
        <div className="annot-actions">
          <button type="button" onClick={save}>Salvar transcrição e comparar com o currículo</button>
        </div>
        <p className="annot-note">Depois de salva, a fase 1 fica travada; reabri-la apaga a fase 2 deste caso e é registrado no arquivo exportado.</p>
      </section>
    </div>
  )
}
