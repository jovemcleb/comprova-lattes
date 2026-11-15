import { useState } from 'react'
import {
  applyAsyncOcrFailure,
  applyAsyncOcrResult,
  caseStage,
  optInDraftToOcrAssisted,
  persistDraft,
  type CaseAnnotation,
  type ReviewDraft,
} from '../lib/annotation/draft'
import type { VerifiedOcrResponse } from '../lib/annotation/ocr'
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
    setDraft(current => {
      if (!current || !current.cases[caseId]) return current
      const next: ReviewDraft = {
        ...current,
        updated_at: new Date().toISOString(),
        cases: { ...current.cases, [caseId]: update(current.cases[caseId]) },
      }
      setStorageOk(persistDraft(next))
      return next
    })
  }

  function handleOptInAndRead() {
    setDraft(current => {
      if (!current) return current
      const { upgraded, storageOk: ok } = optInDraftToOcrAssisted(current)
      setStorageOk(ok)
      return upgraded
    })
  }

  function handleOcrSuccess(caseId: string, response: VerifiedOcrResponse) {
    setDraft(current => {
      if (!current || !current.cases[caseId]) return current
      if (current.review_mode === 'unassisted') {
        persistDraft(current)
      }
      const next = applyAsyncOcrResult(current, caseId, response)
      setStorageOk(persistDraft(next))
      return next
    })
  }

  function handleOcrFailure(caseId: string, errorMessage: string) {
    setDraft(current => {
      if (!current || !current.cases[caseId]) return current
      if (current.review_mode === 'unassisted') {
        persistDraft(current)
      }
      const next = applyAsyncOcrFailure(current, caseId, errorMessage)
      setStorageOk(persistDraft(next))
      return next
    })
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
          <strong>Separada dos pareceres operacionais.</strong> Esta página não usa a API principal nem o banco, não registra parecer AD-013 e
          não envia dados a Gemini. As respostas servem à avaliação experimental do piloto; consenso e Kappa são etapas posteriores, fora desta
          tela.
        </p>
        <p>
          <strong>Auxílio OCR opcional (Tesseract local):</strong> o botão <span className="code">Ler com OCR</span> é opt-in e consulta apenas
          o serviço local offline (<span className="code">127.0.0.1:8766</span>) com os bytes do comprovante. Quando acionado antes da conclusão
          do caso, a sessão é registrada como <strong>revisão humana assistida</strong> (<span className="code">ocr_assisted_human_review</span>),
          distinta da anotação humana independente sem auxílio e sujeita a potencial viés pró-baseline (<span className="code">TesseractOCR</span>{' '}
          + <span className="code">OCRRegex</span>). Sem o serviço OCR ativo, a revisão manual funciona integralmente.
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
              Revisor declarado: <strong>{draft.reviewer}</strong> · modo{' '}
              <span className="code">
                {draft.review_mode === 'ocr_assisted' ? 'ocr_assisted (revisão assistida por OCR)' : 'unassisted (manual sem auxílio)'}
              </span>{' '}
              · condição <span className="code">{draft.evaluation_condition}</span> · guia{' '}
              <span className="code">{draft.guide_version}</span> · pacote{' '}
              <span className="code">{draft.package_sha256.slice(0, 12)}…</span>
              {resumed && ' · progresso local retomado'}
              {draft.migrated_from_export_version && ` · migrado de ${draft.migrated_from_export_version}`}
            </p>
            {!storageOk && (
              <p className="error" role="alert">
                Salvamento local indisponível neste navegador. Exporte o rascunho em JSON com frequência para não perder o trabalho.
              </p>
            )}
            <button type="button" className="secondary" onClick={reset}>Trocar revisor, modo ou pacote</button>
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

                  </div>
                  {annotation.phase1.status === 'saved' ? (
                    <ComparisonPhase
                      key={pkgCase.case_id}
                      pkgCase={pkgCase}
                      annotation={annotation}
                      onChange={update => updateCase(pkgCase.case_id, update)}
                    />
                  ) : (
                    <DocumentPhase
                      key={pkgCase.case_id}
                      pkgCase={pkgCase}
                      annotation={annotation}
                      reviewMode={draft.review_mode}
                      onChange={update => updateCase(pkgCase.case_id, update)}
                      onOptInAndRead={handleOptInAndRead}
                      onOcrSuccess={handleOcrSuccess}
                      onOcrFailure={handleOcrFailure}
                    />
                  )}
                  <nav className="annot-case-navigation" aria-label="Navegação entre avaliações">
                    <button type="button" className="secondary" disabled={index === 0} onClick={() => {
                      setSelectedId(pkg.cases[index - 1].case_id)
                      document.getElementById('annot-case-title')?.scrollIntoView({ block: 'start' })
                    }}>Anterior</button>
                    <span className="annot-note">Caso {index + 1} de {pkg.cases.length} · progresso salvo automaticamente</span>
                    <button type="button" className="secondary" disabled={index === pkg.cases.length - 1} onClick={() => {
                      setSelectedId(pkg.cases[index + 1].case_id)
                      document.getElementById('annot-case-title')?.scrollIntoView({ block: 'start' })
                    }}>Próximo</button>
                  </nav>
                </section>
              )}
              <DraftControls pkg={pkg} draft={draft} onImport={commit} storageUnavailable={!storageOk} />
            </div>
          </div>
        </>
      )}
    </>
  )
}
