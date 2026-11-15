import { useState } from 'react'
import type { PackageCase } from '../../lib/annotation/package'
import {
  emptyPhase2,
  FIELD_DEFS,
  FIELD_STATES,
  validatePhase1,
  type CaseAnnotation,
  type FieldKey,
  type FieldState,
} from '../../lib/annotation/draft'
import { DocumentViewer } from './DocumentViewer'
import { ErrorSummary } from './ErrorSummary'
import { RadioGroup } from './RadioGroup'

export type CaseUpdater = (update: (annotation: CaseAnnotation) => CaseAnnotation) => void

interface DocumentPhaseProps {
  pkgCase: PackageCase
  annotation: CaseAnnotation
  onChange: CaseUpdater
}

/** Fase 1: transcrição do documento em branco, sem XML, sugestões ou valores de outra fonte. */
export function DocumentPhase({ pkgCase, annotation, onChange }: DocumentPhaseProps) {
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
        <h3 id={`phase1-${pkgCase.case_id}`}>Fase 1 · Transcrição do documento</h3>
        {document ? (
          <p>
            Transcreva somente o que está visível no comprovante. O registro XML e qualquer sugestão ficam ocultos até esta fase ser salva.
            Para cada campo, marque <strong>presente</strong> (com o valor literal), <strong>ausente</strong> (não consta) ou{' '}
            <strong>ilegível</strong> (consta, mas não dá para ler). Ausente e ilegível são estados distintos.
          </p>
        ) : (
          <div className="attention">
            <p>
              <strong>Este caso não possui documento.</strong> A transcrição está desativada e nada é preenchido ou classificado
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
          return (
            <div className="annot-field" key={def.key}>
              <RadioGroup
                legend={def.label}
                name={name}
                options={FIELD_STATES}
                value={field.state}
                disabled={document === null}
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
            </div>
          )
        })}
        <ErrorSummary problems={problems} />
        <div className="annot-actions">
          <button type="button" onClick={save}>Salvar fase 1 e abrir comparação</button>
        </div>
        <p className="annot-note">Depois de salva, a fase 1 fica travada; reabri-la apaga a fase 2 deste caso e é registrado no arquivo exportado.</p>
      </section>
    </div>
  )
}
