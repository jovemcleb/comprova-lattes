import { useState } from 'react'
import type { AnnotationPackage } from '../../lib/annotation/package'
import {
  buildExport,
  exportFilename,
  incompleteCases,
  parseExport,
  persistDraft,
  type ReviewDraft,
} from '../../lib/annotation/draft'

interface DraftControlsProps {
  pkg: AnnotationPackage
  draft: ReviewDraft
  onImport: (draft: ReviewDraft) => void
}

function download(filename: string, content: string) {
  const url = URL.createObjectURL(new Blob([content], { type: 'application/json' }))
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

export function DraftControls({ pkg, draft, onImport }: DraftControlsProps) {
  const [message, setMessage] = useState<{ kind: 'ok' | 'error'; text: string } | null>(null)
  const pending = incompleteCases(draft, pkg)

  async function exportAs(kind: 'draft' | 'final') {
    try {
      const exported = await buildExport(draft, pkg, kind)
      download(exportFilename(draft, kind), JSON.stringify(exported, null, 2))
      setMessage({
        kind: 'ok',
        text:
          kind === 'final'
            ? `Exportação final validada (${pkg.cases.length} casos). annotation_sha256: ${exported.annotation_sha256}`
            : `Rascunho exportado. annotation_sha256: ${exported.annotation_sha256}. Rascunho não serve para concordância nem Kappa.`,
      })
    } catch (failure) {
      setMessage({ kind: 'error', text: failure instanceof Error ? failure.message : 'Falha ao exportar.' })
    }
  }

  async function importDraft(file: File | undefined) {
    if (!file) return
    try {
      const imported = await parseExport(await file.text(), pkg, draft.reviewer)
      persistDraft(imported)
      onImport(imported)
      setMessage({ kind: 'ok', text: 'Rascunho importado e validado; substituiu o progresso local deste revisor.' })
    } catch (failure) {
      setMessage({ kind: 'error', text: `Importação rejeitada: ${failure instanceof Error ? failure.message : 'arquivo inválido.'}` })
    }
  }

  return (
    <section className="panel" aria-labelledby="annot-export-title">
      <h2 id="annot-export-title">Salvar e exportar</h2>
      <p className="annot-note">
        O progresso é salvo automaticamente neste navegador. Exporte o JSON para ter cópia fora do navegador. O arquivo traz revisor, versão do
        guia e hashes do pacote, dos documentos e do XML. Esta tela não calcula Kappa, concordância nem consenso.
      </p>
      <div className="annot-actions">
        <button type="button" className="secondary" onClick={() => void exportAs('draft')}>Exportar rascunho (JSON)</button>
        <button type="button" disabled={pending.length > 0} onClick={() => void exportAs('final')}>Exportar final validado (JSON)</button>
      </div>
      {pending.length > 0 && <p className="annot-note">Exportação final liberada somente com os {pkg.cases.length} casos completos; faltam {pending.length}.</p>}
      <label>
        Importar rascunho deste revisor (.json)
        <input type="file" accept="application/json,.json" onChange={event => { void importDraft(event.target.files?.[0]); event.target.value = '' }} />
      </label>
      <p className="annot-note">Importar substitui o progresso local do revisor atual. Rascunho de outro revisor ou de outro pacote é rejeitado.</p>
      {message && (
        <p role={message.kind === 'error' ? 'alert' : 'status'} className={message.kind === 'error' ? 'error' : undefined}>
          {message.text}
        </p>
      )}
    </section>
  )
}
