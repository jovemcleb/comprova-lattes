import { useState, type FormEvent } from 'react'
import type { AnnotationPackage } from '../../lib/annotation/package'
import {
  discardStoredDraft,
  inspectStoredModes,
  loadStoredDraft,
  newDraft,
  normalizeReviewer,
  persistDraft,
  progressOf,
  reviewerProblem,
  type ReviewDraft,
  type ReviewMode,
} from '../../lib/annotation/draft'
import { RadioGroup } from './RadioGroup'

interface ReviewerGateProps {
  pkg: AnnotationPackage
  onStart: (draft: ReviewDraft, resumed: boolean, storageOk: boolean) => void
  onChangePackage: () => void
}

const MODE_OPTIONS: readonly { value: ReviewMode; label: string }[] = [
  { value: 'unassisted', label: 'Revisão manual sem auxílio (padrão — independente)' },
  { value: 'ocr_assisted', label: 'Revisão assistida por OCR local (opt-in — sujeita a viés de baseline)' },
]

export function ReviewerGate({ pkg, onStart, onChangePackage }: ReviewerGateProps) {
  const [reviewer, setReviewer] = useState('')
  const [reviewMode, setReviewMode] = useState<ReviewMode>('unassisted')
  const [problem, setProblem] = useState<string | null>(null)
  const [corrupt, setCorrupt] = useState<string | null>(null)

  const validReviewer = reviewerProblem(reviewer) === null ? normalizeReviewer(reviewer) : null
  const storedSummary = validReviewer ? inspectStoredModes(pkg, validReviewer) : null

  function start(event: FormEvent) {
    event.preventDefault()
    const invalid = reviewerProblem(reviewer)
    setProblem(invalid)
    setCorrupt(null)
    if (invalid) return
    const name = normalizeReviewer(reviewer)
    const stored = loadStoredDraft(pkg, name, reviewMode)
    if (stored.kind === 'corrupt') {
      setCorrupt(stored.message)
      return
    }
    if (stored.kind === 'ok') {
      onStart(stored.draft, true, true)
      return
    }
    const draft = newDraft(pkg, name, new Date(), reviewMode)
    onStart(draft, false, persistDraft(draft))
  }

  function discardAndStart() {
    const name = normalizeReviewer(reviewer)
    discardStoredDraft(pkg, name, reviewMode)
    const draft = newDraft(pkg, name, new Date(), reviewMode)
    onStart(draft, false, persistDraft(draft))
  }

  return (
    <section className="panel" aria-labelledby="annot-reviewer-title">
      <h2 id="annot-reviewer-title">2. Declarar revisor e modo de revisão</h2>
      <dl className="annot-record">
        <dt>Casos</dt>
        <dd>{pkg.cases.length}</dd>
        <dt>Guia</dt>
        <dd className="code">{pkg.guide_version}</dd>
        <dt>Hash do pacote</dt>
        <dd className="code">{pkg.package_sha256}</dd>
      </dl>
      <div className="annot-banner">
        <p>
          <strong>Isolamento local e separação entre modos (assistido vs. não assistido).</strong> O progresso fica no armazenamento deste
          navegador e perfil, separado por hash do pacote, revisor e modo de revisão (<span className="code">unassisted</span> vs.{' '}
          <span className="code">ocr_assisted</span>). Rascunhos manuais e rascunhos assistidos por OCR nunca são misturados silenciosamente.
        </p>
        <p>
          Para manter a independência, cada revisor deve usar seu próprio perfil ou computador e exportar o JSON. Respostas de outro revisor
          nunca são exibidas aqui.
        </p>
      </div>
      <form onSubmit={start} noValidate>
        <label>
          Nome ou identificador do revisor
          <input
            value={reviewer}
            onChange={event => {
              setReviewer(event.target.value)
              setProblem(null)
              setCorrupt(null)
            }}
            autoComplete="off"
            aria-invalid={problem ? true : undefined}
            aria-describedby={problem ? 'annot-reviewer-error' : undefined}
          />
        </label>

        <div className="annot-field">
          <RadioGroup<ReviewMode>
            legend="Condição metodológica da sessão"
            name="annot-review-mode"
            options={MODE_OPTIONS}
            value={reviewMode}
            hint="O modo assistido habilita o painel TesseractOCR + OCRRegex na Fase 1, registrando revisão humana assistida no JSON exportado (não equivale a anotação independente sem auxílio)."
            onChange={mode => {
              setReviewMode(mode)
              setCorrupt(null)
            }}
          />
        </div>

        {storedSummary && (storedSummary.unassisted.kind === 'ok' || storedSummary.ocr_assisted.kind === 'ok') && (
          <div className="annot-note" role="status">
            <strong>Rascunhos locais encontrados para {validReviewer}:</strong>
            <ul>
              {storedSummary.unassisted.kind === 'ok' && (
                <li>
                  Modo manual (<span className="code">unassisted</span>):{' '}
                  {progressOf(storedSummary.unassisted.draft).complete} de {pkg.cases.length} concluídos
                  {storedSummary.unassisted.draft.migrated_from_export_version
                    ? ` (migrado de ${storedSummary.unassisted.draft.migrated_from_export_version}, original preservado)`
                    : ''}
                </li>
              )}
              {storedSummary.ocr_assisted.kind === 'ok' && (
                <li>
                  Modo assistido por OCR (<span className="code">ocr_assisted</span>):{' '}
                  {progressOf(storedSummary.ocr_assisted.draft).complete} de {pkg.cases.length} concluídos (
                  {progressOf(storedSummary.ocr_assisted.draft).ocrAssistedCases} caso(s) com OCR acionado)
                </li>
              )}
            </ul>
          </div>
        )}

        {problem && (
          <p id="annot-reviewer-error" className="error" role="alert">
            {problem}
          </p>
        )}
        {corrupt && (
          <div className="error" role="alert">
            <p>O rascunho local deste revisor no modo selecionado está inválido: {corrupt}</p>
            <button type="button" className="secondary" onClick={discardAndStart}>
              Descartar rascunho deste modo e começar vazio
            </button>
          </div>
        )}
        <div className="annot-actions">
          <button type="submit">Iniciar ou continuar revisão</button>
          <button type="button" className="secondary" onClick={onChangePackage}>
            Trocar pacote
          </button>
        </div>
      </form>
    </section>
  )
}
