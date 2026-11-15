import { useState } from 'react'
import { caseStage, persistDraft, type CaseAnnotation, type ReviewDraft } from '../lib/annotation/draft'
import type { AnnotationPackage } from '../lib/annotation/package'
import { CaseList } from '../components/annotation/CaseList'
import { ComparisonPhase } from '../components/annotation/ComparisonPhase'
import { DocumentPhase } from '../components/annotation/DocumentPhase'
import { DraftControls } from '../components/annotation/DraftControls'
import { PackageImport } from '../components/annotation/PackageImport'
import { ReviewerGate } from '../components/annotation/ReviewerGate'
import '../components/annotation/annotation.css'

export function ExperimentalReviewPage() {
  const [pkg, setPkg] = useState<AnnotationPackage | null>(null)
  const [draft, setDraft] = useState<ReviewDraft | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [storageOk, setStorageOk] = useState(true)
  const [resumed, setResumed] = useState(false)

  function commit(next: ReviewDraft) {
    setStorageOk(persistDraft(next))
    setDraft(next)
  }

  function updateCase(caseId: string, update: (annotation: CaseAnnotation) => CaseAnnotation) {
    if (!draft) return
    commit({ ...draft, updated_at: new Date().toISOString(), cases: { ...draft.cases, [caseId]: update(draft.cases[caseId]) } })
  }

  function reset() {
    setPkg(null)
    setDraft(null)
    setSelectedId(null)
  }

  const index = pkg && selectedId ? pkg.cases.findIndex(item => item.case_id === selectedId) : -1
  const pkgCase = pkg && index >= 0 ? pkg.cases[index] : null
  const annotation = pkgCase && draft ? draft.cases[pkgCase.case_id] : null

  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">Revisão experimental</p>
          <h1>Anotação humana do piloto</h1>
        </div>
      </div>
      <div className="annot-banner">
        <p>
          <strong>Separada dos pareceres operacionais.</strong> Esta página não usa a API nem o banco, não registra parecer AD-013 e não envia
          dados a Gemini. As respostas servem à anotação independente do protocolo experimental; consenso e Kappa são etapas posteriores,
          fora desta tela.
        </p>
      </div>

      {!pkg && <PackageImport onLoaded={setPkg} />}
      {pkg && !draft && (
        <ReviewerGate
          pkg={pkg}
          onChangePackage={reset}
          onStart={(started, wasResumed, ok) => {
            setDraft(started)
            setResumed(wasResumed)
            setStorageOk(ok)
            const firstOpen = pkg.cases.find(item => caseStage(started.cases[item.case_id]) !== 'complete')
            setSelectedId((firstOpen ?? pkg.cases[0]).case_id)
          }}
        />
      )}

      {pkg && draft && (
        <>
          <section className="panel" aria-label="Sessão de revisão">
            <p>
              Revisor declarado: <strong>{draft.reviewer}</strong> · guia <span className="code">{draft.guide_version}</span> · pacote{' '}
              <span className="code">{draft.package_sha256.slice(0, 12)}…</span>
              {resumed && ' · progresso local retomado'}
            </p>
            {!storageOk && (
              <p className="error" role="alert">
                Salvamento local indisponível neste navegador. Exporte o rascunho em JSON com frequência para não perder o trabalho.
              </p>
            )}
            <button type="button" className="secondary" onClick={reset}>Trocar revisor ou pacote</button>
          </section>

          <div className="annot-layout">
            <CaseList pkg={pkg} draft={draft} selectedId={selectedId ?? ''} onSelect={setSelectedId} />
            <div>
              {pkgCase && annotation && (
                <section className="panel" aria-labelledby="annot-case-title">
                  <div className="page-heading">
                    <h2 id="annot-case-title">
                      {pkgCase.case_id} <small>({index + 1} de {pkg.cases.length})</small>
                    </h2>
                    <div>
                      <button type="button" className="secondary" disabled={index === 0} onClick={() => setSelectedId(pkg.cases[index - 1].case_id)}>Anterior</button>
                      <button type="button" className="secondary" disabled={index === pkg.cases.length - 1} onClick={() => setSelectedId(pkg.cases[index + 1].case_id)}>Próximo</button>
                    </div>
                  </div>
                  {annotation.phase1.status === 'saved' ? (
                    <ComparisonPhase key={pkgCase.case_id} pkgCase={pkgCase} annotation={annotation} onChange={update => updateCase(pkgCase.case_id, update)} />
                  ) : (
                    <DocumentPhase key={pkgCase.case_id} pkgCase={pkgCase} annotation={annotation} onChange={update => updateCase(pkgCase.case_id, update)} />
                  )}
                </section>
              )}
              <DraftControls pkg={pkg} draft={draft} onImport={commit} />
            </div>
          </div>
        </>
      )}
    </>
  )
}
