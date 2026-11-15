import type { AnnotationPackage } from '../../lib/annotation/package'
import {
  caseStage,
  isCaseOcrAssisted,
  progressOf,
  type CaseStage,
  type ReviewDraft,
} from '../../lib/annotation/draft'

const STAGE_LABEL: Record<CaseStage, string> = {
  not_started: 'Não iniciado',
  phase1: 'Fase 1 em curso',
  phase2: 'Fase 2 pendente',
  complete: 'Concluído',
}

interface CaseListProps {
  pkg: AnnotationPackage
  draft: ReviewDraft
  selectedId: string
  onSelect: (caseId: string) => void
}

export function CaseList({ pkg, draft, selectedId, onSelect }: CaseListProps) {
  const progress = progressOf(draft)
  const percent = progress.total ? Math.round((progress.complete / progress.total) * 100) : 0
  return (
    <aside aria-label="Casos e progresso">
      <h2>Casos</h2>
      <p>
        <strong>{progress.complete}</strong> de {progress.total} concluídos · fase 1 salva em {progress.phase1Saved}
        {progress.ocrAssistedCases > 0 && ` · OCR em ${progress.ocrAssistedCases}`}
      </p>
      <div className="annot-progress" role="progressbar" aria-label="Progresso de casos concluídos" aria-valuemin={0} aria-valuemax={progress.total} aria-valuenow={progress.complete}>
        <span style={{ width: `${percent}%` }} />
      </div>
      <nav aria-label="Lista de casos">
        <ol className="annot-cases">
          {pkg.cases.map(item => {
            const annotation = draft.cases[item.case_id]
            const stage = caseStage(annotation)
            const usedOcr = isCaseOcrAssisted(annotation.ocr_assistance)
            return (
              <li key={item.case_id}>
                <button type="button" aria-current={item.case_id === selectedId} onClick={() => onSelect(item.case_id)}>
                  <span>
                    {item.case_id}
                    {usedOcr ? ' (OCR)' : ''}
                  </span>
                  <span className={stage === 'complete' ? 'badge success' : 'badge'}>{STAGE_LABEL[stage]}</span>
                </button>
              </li>
            )
          })}
        </ol>
      </nav>
    </aside>
  )
}
