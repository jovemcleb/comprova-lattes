import { Link, Route, Routes } from 'react-router'

function Home() {
  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col justify-center px-6 py-16">
      <span className="mb-4 text-sm font-semibold uppercase tracking-widest text-emerald-700">Comprova Lattes</span>
      <h1 className="text-4xl font-bold tracking-tight text-slate-950 sm:text-6xl">Validação acadêmica rastreável.</h1>
      <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-600">
        Compare registros do Currículo Lattes com documentos comprobatórios e entenda cada campo do resultado.
      </p>
      <Link className="mt-8 w-fit rounded-lg bg-emerald-700 px-5 py-3 font-semibold text-white hover:bg-emerald-800" to="/validacoes/nova">
        Nova validação
      </Link>
    </main>
  )
}

function NewValidation() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-16">
      <Link className="text-sm font-semibold text-emerald-700" to="/">← Voltar</Link>
      <h1 className="mt-8 text-3xl font-bold text-slate-950">Nova validação</h1>
      <p className="mt-3 text-slate-600">Fluxo de upload será implementado no próximo marco.</p>
    </main>
  )
}

export default function App() {
  return (
    <Routes>
      <Route element={<Home />} path="/" />
      <Route element={<NewValidation />} path="/validacoes/nova" />
    </Routes>
  )
}
