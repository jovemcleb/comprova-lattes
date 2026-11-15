import { useState } from 'react'
import type { AnnotationPackage } from '../../lib/annotation/package'
import {
  EXPORT_VERSION,
  EXPORT_VERSION_V1,
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
  storageUnavailable?: boolean
}

function download(filename: string, content: string) {
  const url = URL.createObjectURL(new Blob([content], { type: 'application/json' }))
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

export function DraftControls({ pkg, draft, onImport, storageUnavailable = false }: DraftControlsProps) {
  const [message, setMessage] = useState<{ kind: 'ok' | 'error'; text: string } | null>(null)
  const [allowModeSwitch, setAllowModeSwitch] = useState(false)
  const pending = incompleteCases(draft, pkg)

  async function exportAs(kind: 'draft' | 'final') {
    try {
      const exported = await buildExport(draft, pkg, kind)
      download(exportFilename(draft, kind), JSON.stringify(exported, null, 2))
      setMessage({
        kind: 'ok',
        text:
          kind === 'final'
            ? `Exportação final validada (${pkg.cases.length} casos · ${exported.export_version} · condição ${exported.evaluation_condition}). annotation_sha256: ${exported.annotation_sha256}`
            : `Rascunho exportado (${exported.export_version} · modo ${exported.review_mode}). annotation_sha256: ${exported.annotation_sha256}. Rascunho não serve para concordância nem Kappa.`,
      })
    } catch (failure) {
      setMessage({ kind: 'error', text: failure instanceof Error ? failure.message : 'Falha ao exportar.' })
    }
  }

  async function importDraft(file: File | undefined) {
    if (!file) return
    try {
      const imported = await parseExport(await file.text(), pkg, draft.reviewer, {
        expectedMode: draft.review_mode,
        allowModeSwitch,
      })
      if (imported.review_mode !== draft.review_mode) {
        persistDraft(draft)
      }
      persistDraft(imported)
      onImport(imported)
      const migrationNote =
        imported.migrated_from_export_version === EXPORT_VERSION_V1
          ? ` (migrado de ${EXPORT_VERSION_V1} como não assistido)`
          : ''
      setMessage({
        kind: 'ok',
        text: `Arquivo importado e validado no modo "${imported.review_mode}"${migrationNote}; substituiu o progresso local deste modo para o revisor atual.`,
      })
    } catch (failure) {
      setMessage({ kind: 'error', text: `Importação rejeitada: ${failure instanceof Error ? failure.message : 'arquivo inválido.'}` })
    }
  }

  return (
    <section className="panel" aria-label="Backup e conclusão da revisão">
      {pending.length === 0 && (
        <div className="annot-review-complete">
          <h2>Revisão concluída</h2>
          <p>Você concluiu os {pkg.cases.length} casos. Exporte suas respostas para guardar e entregar sua avaliação.</p>
          <button type="button" onClick={() => void exportAs('final')}>Exportar avaliação final (JSON)</button>
          <p className="annot-note">O arquivo contém somente as respostas deste revisor. O consenso é registrado separadamente.</p>
        </div>
      )}
      <details className="annot-backup" open={storageUnavailable || undefined}>
        <summary>{storageUnavailable ? 'Atenção: baixe um backup para não perder suas respostas' : 'Pausar, baixar backup ou retomar de um arquivo'}</summary>
        <p className="annot-note">O progresso é salvo automaticamente neste navegador. Se precisar parar, trocar de computador ou guardar uma cópia, baixe um rascunho. Ele não é a entrega final.</p>
        <button type="button" className="secondary" onClick={() => void exportAs('draft')}>Baixar backup do rascunho (JSON)</button>
      <label>
        Importar rascunho/exportação deste revisor (.json — aceita {EXPORT_VERSION_V1} e {EXPORT_VERSION})
        <input type="file" accept="application/json,.json" onChange={event => { void importDraft(event.target.files?.[0]); event.target.value = '' }} />
      </label>
      <label className="checkbox">
        <input
          type="checkbox"
          checked={allowModeSwitch}
          onChange={event => setAllowModeSwitch(event.target.checked)}
        />
        Permitir alternar o modo da sessão ao importar arquivo de outro modo (o rascunho do modo atual permanece salvo separadamente)
      </label>
      <p className="annot-note">
        Por padrão, arquivos assistidos (<span className="code">ocr_assisted</span>) e não assistidos (<span className="code">unassisted</span>)
        não se misturam silenciosamente. Rascunho de outro revisor ou de outro pacote é sempre rejeitado.
      </p>
      </details>
      {message && (
        <p role={message.kind === 'error' ? 'alert' : 'status'} className={message.kind === 'error' ? 'error' : undefined}>
          {message.text}
        </p>
      )}
    </section>
  )
}
