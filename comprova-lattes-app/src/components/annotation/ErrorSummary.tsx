const focusOnMount = (node: HTMLElement | null) => {
  node?.focus()
}

export function ErrorSummary({ problems }: { problems: string[] }) {
  if (!problems.length) return null
  return (
    <div className="annot-errors" role="alert" tabIndex={-1} ref={focusOnMount}>
      <strong>Corrija antes de salvar:</strong>
      <ul>
        {problems.map(problem => (
          <li key={problem}>{problem}</li>
        ))}
      </ul>
    </div>
  )
}
