import { useState, type FormEvent } from 'react'
import type { AnnotationPackage } from '../../lib/annotation/package'
import {
  discardStoredDraft,
  loadStoredDraft,
  newDraft,
  normalizeReviewer,
  persistDraft,
  reviewerProblem,
  type ReviewDraft,
} from '../../lib/annotation/draft'

interface ReviewerGateProps {
  pkg: AnnotationPackage
  onStart: (draft: ReviewDraft, resumed: boolean, storageOk: boolean) => void
  onChangePackage: () => void
}

export function ReviewerGate({ pkg, onStart, onChangePackage }: ReviewerGateProps) {
  const [reviewer, setReviewer] = useState('')
  const [problem, setProblem] = useState<string | null>(null)
  const [corrupt, setCorrupt] = useState<string | null>(null)

  function start(event: FormEvent) {
    event.preventDefault()
    const invalid = reviewerProblem(reviewer)
    setProblem(invalid)
    setCorrupt(null)
    if (invalid) return
    const name = normalizeReviewer(reviewer)
    const stored = loadStoredDraft(pkg, name)
    if (stored.kind === 'corrupt') {
      setCorrupt(stored.message)
      return
    }
    if (stored.kind === 'ok') {
      onStart(stored.draft, true, true)
      return
    }
    const draft = newDraft(pkg, name)
    onStart(draft, false, persistDraft(draft))
  }

  function discardAndStart() {
    const name = normalizeReviewer(reviewer)
    discardStoredDraft(pkg, name)
    const draft = newDraft(pkg, name)
    onStart(draft, false, persistDraft(draft))
  }

  return (
    <section className="panel" aria-labelledby="annot-reviewer-title">
      <h2 id="annot-reviewer-title">2. Declarar revisor</h2>
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
          <strong>Isolamento local, não autenticação.</strong> O progresso fica no armazenamento deste navegador e perfil, separado por nome de
          revisor e por hash do pacote. Isso apenas evita misturar anotações por engano: qualquer pessoa com acesso ao mesmo perfil pode abrir
          ou apagar os dados de qualquer revisor.
        </p>
        <p>Para manter a independência, cada revisor deve usar seu próprio perfil ou computador e exportar o JSON. Respostas de outro revisor nunca são exibidas aqui.</p>
      </div>
      <form onSubmit={start} noValidate>
        <label>
          Nome ou identificador do revisor
          <input value={reviewer} onChange={event => { setReviewer(event.target.value); setProblem(null); setCorrupt(null) }} autoComplete="off" aria-invalid={problem ? true : undefined} aria-describedby={problem ? 'annot-reviewer-error' : undefined} />
        </label>
        {problem && <p id="annot-reviewer-error" className="error" role="alert">{problem}</p>}
        {corrupt && (
          <div className="error" role="alert">
            <p>O rascunho local deste revisor está inválido: {corrupt}</p>
            <button type="button" className="secondary" onClick={discardAndStart}>Descartar rascunho local e começar vazio</button>
          </div>
        )}
        <div className="annot-actions">
          <button type="submit">Iniciar ou continuar revisão</button>
          <button type="button" className="secondary" onClick={onChangePackage}>Trocar pacote</button>
        </div>
      </form>
    </section>
  )
}
