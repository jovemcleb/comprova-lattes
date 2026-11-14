export function AuditData({ title, data }: { title: string; data: unknown }) {
  return <details className="audit-data"><summary>{title}</summary><pre>{JSON.stringify(data, null, 2) ?? 'Não disponível'}</pre></details>
}
export function ErrorNotice({ error }: { error: Error | null }) {
  return error ? <p role="alert" className="error">{error.message}</p> : null
}
