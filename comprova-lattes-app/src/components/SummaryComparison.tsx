import type { ValidationDetail } from '../types/validation'
export function SummaryComparison({ validation }: { validation: ValidationDetail }) {
  const summaries = [{ title: 'Automático · pré-revisão', counts: validation.automatic_summary }, { title: 'Após revisão · último parecer ou automático', counts: validation.reviewed_summary }]
  return <section><h2>Resultado e revisão</h2><p>Contagens operacionais, sem representar métricas científicas. O resultado automático é preservado.</p><div className="grid gap-4 md:grid-cols-2">{summaries.map(({ title, counts }) => <div className="panel" key={title}><h3>{title}</h3><dl className="counts">{Object.entries(counts).map(([label, count]) => <div key={label}><dt>{label}</dt><dd>{count}</dd></div>)}</dl></div>)}</div></section>
}
