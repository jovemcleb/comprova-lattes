import sys
sys.path.insert(0, "/s")
import analyze as A
el, at = A.parse_dtd(A.DTD)
defs, *_ = A.parse_xsd(A.XSD)
for n in ["CURRICULO-VITAE", "DADOS-GERAIS", "RESUMO-CV", "DADOS-COMPLEMENTARES"]:
    d, x = at.get(n, {}), defs[n]["attrs"]
    dr = sorted(a for a, v in d.items() if v["default"] == "#REQUIRED")
    xr = sorted(a for a, v in x.items() if v["use"] == "required")
    print(n, "\n  DTD required:", dr, "\n  XSD required:", xr, "\n  dtd_only:", sorted(set(d) - set(x)), "\n  xsd_only:", sorted(set(x) - set(d)))
    fx = {a: v["default"] for a, v in d.items() if v["default"].startswith('#FIXED') or (not v["default"].startswith("#"))}
    print("  DTD fixed/default values:", fx)
    print("  XSD fixed/default:", {a: v["fixed"] for a, v in x.items() if v["fixed"]})
# fields the xml-mapping/parser relies on, checked against both grammars
need = {
 "GRADUACAO": ["SEQUENCIA-FORMACAO","NOME-INSTITUICAO","SIGLA-INSTITUICAO","NOME-CURSO","NOME-CURSO-INGLES","TITULO-DA-DISSERTACAO-TESE","TITULO-DO-TRABALHO-DE-CONCLUSAO-DE-CURSO","ANO-DE-INICIO","ANO-DE-CONCLUSAO","ANO-DE-OBTENCAO-DO-TITULO","CARGA-HORARIA","STATUS-DO-CURSO","CODIGO-CURSO-CAPES"],
 "MESTRADO": ["TITULO-DA-DISSERTACAO-TESE","ANO-DE-OBTENCAO-DO-TITULO","CARGA-HORARIA","SIGLA-INSTITUICAO","STATUS-DO-CURSO"],
 "DOUTORADO": ["TITULO-DA-DISSERTACAO-TESE","ANO-DE-OBTENCAO-DO-TITULO","CARGA-HORARIA","SIGLA-INSTITUICAO"],
 "ESPECIALIZACAO": ["CARGA-HORARIA","TITULO-DA-MONOGRAFIA","SIGLA-INSTITUICAO"],
 "APERFEICOAMENTO": ["CARGA-HORARIA"],
 "POS-DOUTORADO": ["CARGA-HORARIA","STATUS-DO-CURSO"],
 "FORMACAO-COMPLEMENTAR-CURSO-DE-CURTA-DURACAO": ["SEQUENCIA-FORMACAO","NOME-INSTITUICAO","SIGLA-INSTITUICAO","NOME-CURSO","NOME-CURSO-INGLES","ANO-DE-INICIO","ANO-DE-CONCLUSAO","CARGA-HORARIA","STATUS-DO-CURSO"],
 "MBA": ["CARGA-HORARIA","STATUS-DO-CURSO","ANO-DE-OBTENCAO-DO-TITULO"],
 "DETALHAMENTO-DA-PARTICIPACAO-EM-CONGRESSO": ["NOME-DO-EVENTO","NOME-DO-EVENTO-INGLES","NOME-INSTITUICAO","CIDADE-DO-EVENTO","LOCAL-DO-EVENTO","CARGA-HORARIA"],
 "DADOS-BASICOS-DA-PARTICIPACAO-EM-CONGRESSO": ["TITULO","TITULO-INGLES","ANO","CARGA-HORARIA","NOME-INSTITUICAO"],
 "PARTICIPACAO-EM-CONGRESSO": ["SEQUENCIA-PRODUCAO","SEQUENCIA-FORMACAO"],
 "OUTRAS-PARTICIPACOES-EM-EVENTOS-CONGRESSOS": ["SEQUENCIA-PRODUCAO","TITULO","NOME-DO-EVENTO","CARGA-HORARIA","ANO"],
 "DADOS-BASICOS-DE-OUTRAS-PARTICIPACOES-EM-EVENTOS-CONGRESSOS": ["TITULO","ANO","CARGA-HORARIA"],
 "DETALHAMENTO-DE-OUTRAS-PARTICIPACOES-EM-EVENTOS-CONGRESSOS": ["NOME-DO-EVENTO","NOME-INSTITUICAO","CIDADE-DO-EVENTO","LOCAL-DO-EVENTO","CARGA-HORARIA"],
}
print("\nATTRIBUTE PRESENCE (D=DTD, X=XSD)")
for t, attrs in need.items():
    row = []
    for a in attrs:
        row.append("%s:%s%s" % (a, "D" if a in at.get(t, {}) else "-", "X" if a in defs[t]["attrs"] else "-"))
    print(" ", t, "|", "  ".join(row))
# any CARGA-HORARIA anywhere in the three-section closure
for s in A.SECTIONS:
    stack, seen, hits = [s], set(), []
    while stack:
        n = stack.pop()
        if n in seen: continue
        seen.add(n)
        for k in [c[0] for c in A.flat_children(defs[n]["children"])] if n in defs else []:
            stack.append(k)
        if "CARGA-HORARIA" in defs.get(n, {"attrs": {}})["attrs"]:
            hits.append(n)
    print("CARGA-HORARIA in XSD closure of", s, "->", sorted(hits))
for t in ["SEQUENCIA-PRODUCAO"]:
    pass
# legacy/spec tags not in grammar
tags = ["ENSINO-MEDIO","ENSINO-MEDIO-SEGUNDO-GRAU","ENSINO-FUNDAMENTAL-PRIMEIRO-GRAU","FORMACAO-COMPLEMENTAR-CURTA-DURACAO","OUTROS-TIPOS-DE-FORMACAO-COMPLEMENTAR","OUTROS","OUTRAS-PARTICIPACOES-EM-EVENTOS","OUTRAS-PARTICIPACOES-EM-EVENTOS-CONGRESSOS","PARTICIPACAO-EM-FEIRA","PARTICIPACAO-EM-EXPOSICAO","PARTICIPACAO-EM-OLIMPIADA","MESTRADO-PROFISSIONALIZANTE","POS-DOUTORADO","LIVRE-DOCENCIA","RESIDENCIA-MEDICA","MBA"]
print("\nTAG PRESENCE")
for t in tags:
    print(" ", t, "DTD" if t in el else "-", "XSD" if t in defs else "-")
