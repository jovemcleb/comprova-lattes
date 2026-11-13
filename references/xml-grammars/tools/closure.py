import json, sys
sys.path.insert(0, "/s")
import analyze as A

elements, attlists = A.parse_dtd(A.DTD)
defs, toplevel, other, conflicts, root = A.parse_xsd(A.XSD)

def kids_x(n):
    return [c[0] for c in A.flat_children(defs[n]["children"])] if n in defs else None
def kids_d(n):
    return [c[0] for c in elements[n]["children"]] if n in elements else None

def closure(start):
    seen, stack = [], [start]
    while stack:
        n = stack.pop()
        if n in seen:
            continue
        seen.append(n)
        for k in (kids_x(n) or []) + (kids_d(n) or []):
            stack.append(k)
    return seen

print("XSD DADOS-GERAIS children:", kids_x("DADOS-GERAIS"))
print("DTD DADOS-GERAIS children:", kids_d("DADOS-GERAIS"))
print("XSD DADOS-COMPLEMENTARES children:", kids_x("DADOS-COMPLEMENTARES"))
print("DTD DADOS-COMPLEMENTARES children:", kids_d("DADOS-COMPLEMENTARES"))
print()
# which elements reference each section in each grammar
for s in A.SECTIONS:
    px = [n for n in defs if s in (kids_x(n) or [])]
    pd = [n for n in elements if s in (kids_d(n) or [])]
    print("parents of", s, "xsd", px, "dtd", pd)
print()
total = {"elements": 0, "attr_dtd_only": 0, "attr_xsd_only": 0}
for s in A.SECTIONS:
    print("#######", s)
    for n in closure(s):
        if n == s:
            continue
        inx, ind = n in defs, n in elements
        xa = set(defs[n]["attrs"]) if inx else set()
        da = set(attlists.get(n, {})) if ind else set()
        kx, kd = kids_x(n), kids_d(n)
        notes = []
        if not ind: notes.append("ONLY-XSD")
        if not inx: notes.append("ONLY-DTD")
        if da - xa: notes.append("dtd_only_attrs=%s" % sorted(da - xa))
        if xa - da: notes.append("xsd_only_attrs=%s" % sorted(xa - da))
        if inx and ind and kx != kd: notes.append("children dtd=%s xsd=%s" % (kd, kx))
        # required / enum differences
        if inx and ind:
            for a in sorted(xa & da):
                dd = attlists[n][a]; xx = defs[n]["attrs"][a]
                if (dd["default"] == "#REQUIRED") != (xx["use"] == "required"):
                    notes.append("REQ-mismatch %s" % a)
                de = dd["type"].startswith("ENUM"); xe = str(xx["type"]).startswith("ENUM")
                if de != xe or (de and xe and set(dd["type"][5:-1].split("|")) != set(str(xx["type"])[5:-1].split("|"))):
                    notes.append("ENUM-mismatch %s dtd=%s xsd=%s" % (a, dd["type"], xx["type"]))
        print(("  %s: " % n) + ("; ".join(notes) if notes else "identical attrs/children (names, required, enum)"))
print()
# key attribute types / fixed values in XSD vs DTD for fields used by the parser
for n, a in [("GRADUACAO","STATUS-DO-CURSO"),("GRADUACAO","ANO-DE-INICIO"),("GRADUACAO","ANO-DE-CONCLUSAO"),("GRADUACAO","NIVEL"),("MBA","CARGA-HORARIA"),("OUTROS","CARGA-HORARIA"),("MESTRADO","ANO-DE-OBTENCAO-DO-TITULO"),("MESTRADO","CODIGO-CURSO-CAPES"),("GRADUACAO","SEQUENCIA-FORMACAO")]:
    print(n, a, "DTD:", attlists.get(n, {}).get(a), "XSD:", defs[n]["attrs"].get(a))
