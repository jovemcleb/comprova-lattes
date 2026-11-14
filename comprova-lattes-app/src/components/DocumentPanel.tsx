import type { DocumentInput } from '../types/validation'
export function DocumentPanel({ document }: { document: DocumentInput }) {
  const supported = ['application/pdf', 'image/png', 'image/jpeg', 'image/webp'].includes(document.mime_type)
  if (!supported) return <p>Formato não suportado para visualização.</p>
  const source = `data:${document.mime_type};base64,${document.content_base64}`
  return <details><summary>Documento original · {document.document_id} · {document.filename}</summary><p><a href={source} download={document.filename}>Baixar comprovante original</a></p>{document.mime_type === 'application/pdf' ? <iframe className="document-preview" title={`PDF ${document.filename}`} src={source} sandbox="" /> : <img className="document-image" src={source} alt={`Comprovante ${document.filename}`} loading="lazy" />}<p>Se a prévia não estiver disponível no navegador, baixe o documento.</p></details>
}
