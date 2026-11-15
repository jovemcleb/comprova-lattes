import { useState } from 'react'
import { AnnotationValidationError, MAX_PACKAGE_BYTES, parseAnnotationPackage, type AnnotationPackage } from '../../lib/annotation/package'

export function PackageImport({ onLoaded }: { onLoaded: (pkg: AnnotationPackage) => void }) {
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function handleFile(file: File | undefined) {
    if (!file) return
    setError(null)
    if (file.size > MAX_PACKAGE_BYTES) {
      setError(`Arquivo maior que ${Math.round(MAX_PACKAGE_BYTES / 1024 / 1024)} MB; rejeitado.`)
      return
    }
    setBusy(true)
    try {
      onLoaded(await parseAnnotationPackage(await file.text()))
    } catch (failure) {
      setError(failure instanceof AnnotationValidationError || failure instanceof Error ? failure.message : 'Pacote inválido.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="panel" aria-labelledby="annot-import-title">
      <h2 id="annot-import-title">1. Importar pacote sanitizado</h2>
      <p>
        Selecione o JSON gerado por <span className="code">python -m comprova_lattes.experiments.annotation_package</span>. O arquivo é lido
        apenas neste navegador; esquema, tipos, MIME e hashes são verificados antes de qualquer exibição. Corpus bruto e arquivos com
        gabarito ou metadados internos são rejeitados.
      </p>
      <label>
        Pacote de anotação (.json)
        <input type="file" accept="application/json,.json" disabled={busy} onChange={event => { void handleFile(event.target.files?.[0]); event.target.value = '' }} />
      </label>
      {busy && <p role="status">Validando pacote e hashes…</p>}
      {error && (
        <p className="error" role="alert">
          Pacote rejeitado: {error}
        </p>
      )}
    </section>
  )
}
