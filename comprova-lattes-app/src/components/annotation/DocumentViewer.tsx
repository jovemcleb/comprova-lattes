import { useCallback, useMemo } from 'react'
import { base64ToBytes } from '../../lib/annotation/canonical'
import type { PackageDocument } from '../../lib/annotation/package'

const EXTENSIONS = { 'application/pdf': 'pdf', 'image/png': 'png', 'image/jpeg': 'jpg' } as const

/** Exibe o comprovante via Blob URL local (nada é enviado à rede) e revoga a URL ao desmontar. */
export function DocumentViewer({ document, caseId }: { document: PackageDocument; caseId: string }) {
  const blob = useMemo(
    () => new Blob([base64ToBytes(document.content_base64) as BlobPart], { type: document.mime_type }),
    [document],
  )
  const bindUrl = useCallback(
    (node: HTMLElement | null) => {
      if (!node) return
      const url = URL.createObjectURL(blob)
      if (node instanceof HTMLAnchorElement) node.href = url
      else if (node instanceof HTMLImageElement || node instanceof HTMLIFrameElement) node.src = url
      return () => URL.revokeObjectURL(url)
    },
    [blob],
  )
  const isPdf = document.mime_type === 'application/pdf'
  return (
    <section className="annot-viewer" aria-label={`Comprovante do ${caseId}`}>
      <h3>Comprovante</h3>
      {isPdf ? (
        <iframe ref={bindUrl} className="document-preview" title={`Comprovante PDF do ${caseId}`} />
      ) : (
        <img ref={bindUrl} className="document-image" alt={`Comprovante do ${caseId}`} />
      )}
      <p className="annot-note">
        Se a prévia não aparecer, <a ref={bindUrl} download={`${caseId}.${EXTENSIONS[document.mime_type]}`}>baixe o comprovante</a>.
        Hash SHA-256 verificado na importação: <span className="code">{document.sha256.slice(0, 16)}…</span>
      </p>
    </section>
  )
}
