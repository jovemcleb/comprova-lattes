export function StatusBadge({ status }: { status: string }) {
  const tone = ['VALIDADO', 'COMPLETED', 'MATCH', 'OK'].includes(status) ? 'success' : ['DIVERGENTE', 'FAILED', 'DISPATCH_FAILED', 'CONFLICT'].includes(status) ? 'danger' : 'neutral'
  return <span className={`badge ${tone}`}>{status}</span>
}
