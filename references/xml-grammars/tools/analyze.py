"""Structural analysis of the community DTD and the CNPq XSD (stdlib + lxml for fixtures). Offline."""
import json
import re
import sys
from pathlib import Path

DTD = Path("/g/community-dtd/LMPLCurriculo.DTD")
XSD = Path("/g/cnpq-official/xml_cvbase_src_main_resources_CurriculoLattes_12_09_2022.xsd")
SECTIONS = [
    "FORMACAO-ACADEMICA-TITULACAO",
    "FORMACAO-COMPLEMENTAR",
    "PARTICIPACAO-EM-EVENTOS-CONGRESSOS",
]


# ---------------- DTD ----------------
def parse_dtd(path):
    text = path.read_bytes().decode("iso-8859-1")
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    elements, attlists = {}, {}
    for m in re.finditer(r"<!ELEMENT\s+(\S+)\s+(.*?)>", text, flags=re.S):
        name, model = m.group(1), " ".join(m.group(2).split())
        children = []
        for c in re.finditer(r"([A-Za-z][A-Za-z0-9_.:-]*)\s*([*+?]?)", model):
            if c.group(1) in ("EMPTY", "ANY", "PCDATA"):
                continue
            children.append((c.group(1), c.group(2) or "1"))
        elements[name] = {"model": model, "children": children}
    for m in re.finditer(r"<!ATTLIST\s+(\S+)\s+(.*?)>", text, flags=re.S):
        name, body = m.group(1), m.group(2)
        toks = re.findall(r'"[^"]*"|\([^)]*\)|\S+', body)
        i, attrs = 0, attlists.setdefault(name, {})
        while i < len(toks):
            an = toks[i]
            at = toks[i + 1]
            i += 2
            if toks[i] == "#FIXED":
                dflt = "#FIXED " + toks[i + 1]
                i += 2
            elif toks[i].startswith("#"):
                dflt = toks[i]
                i += 1
            else:
                dflt = toks[i]
                i += 1
            attrs[an] = {"type": at if not at.startswith("(") else "ENUM" + at.replace(" ", ""), "default": dflt}
    return elements, attlists


# ---------------- XSD ----------------
XS = "{http://www.w3.org/2001/XMLSchema}"


def parse_xsd(path):
    from xml.etree import ElementTree as ET

    data = path.read_bytes()
    assert b"<!DOCTYPE" not in data and b"<!ENTITY" not in data
    root = ET.fromstring(data)
    defs, conflicts = {}, []

    def occurs(e):
        return (e.get("minOccurs", "1"), e.get("maxOccurs", "1"))

    def walk_content(node, out):
        for ch in node:
            if ch.tag == XS + "element":
                if ch.get("ref"):
                    out.append((ch.get("ref"),) + occurs(ch))
                else:
                    out.append((ch.get("name"),) + occurs(ch))
                    register(ch)
            elif ch.tag in (XS + "sequence", XS + "choice", XS + "all"):
                sub = []
                walk_content(ch, sub)
                kind = ch.tag.replace(XS, "")
                out.append(("<%s>" % kind, sub, occurs(ch)))

    def simple_enum(st):
        r = st.find(XS + "restriction")
        if r is None:
            return None
        vals = [v.get("value") for v in r.findall(XS + "enumeration")]
        return "ENUM(" + "|".join(vals) + ")" if vals else "restriction:" + r.get("base", "")

    def register(el):
        name = el.get("name")
        rec = {"children": [], "attrs": {}, "type": el.get("type")}
        ct = el.find(XS + "complexType")
        if ct is not None:
            walk_content(ct, rec["children"])
            for a in ct.findall(XS + "attribute"):
                st = a.find(XS + "simpleType")
                t = a.get("type") or (simple_enum(st) if st is not None else None) or "string?"
                rec["attrs"][a.get("name")] = {"type": t, "use": a.get("use", "optional"), "fixed": a.get("fixed")}
            # mixed/simpleContent
            rec["mixed"] = ct.get("mixed")
            rec["has_simple_content"] = ct.find(XS + "simpleContent") is not None
        if name in defs and json.dumps(defs[name], sort_keys=True, default=str) != json.dumps(rec, sort_keys=True, default=str):
            conflicts.append(name)
        defs.setdefault(name, rec)

    for el in root.findall(XS + "element"):
        register(el)
    toplevel = [e.get("name") for e in root.findall(XS + "element")]
    other = [c.tag.replace(XS, "") for c in root if c.tag != XS + "element"]
    return defs, toplevel, other, conflicts, root


def flat_children(ch):
    res = []
    for c in ch:
        if c[0].startswith("<"):
            res.extend(flat_children(c[1]))
        else:
            res.append(c)
    return res


def xsd_tree(defs, name, depth=0, maxd=2, seen=()):
    d = defs.get(name)
    lines = []
    if d is None:
        return ["%s%s  (not defined)" % ("  " * depth, name)]
    attrs = ", ".join("%s[%s]" % (k, "R" if v["use"] == "required" else "o") for k, v in d["attrs"].items())
    lines.append("%s%s  attrs=%s" % ("  " * depth, name, attrs))
    if depth < maxd:
        for c in flat_children(d["children"]):
            lines.extend(xsd_tree(defs, c[0], depth + 1, maxd))
    return lines


def main():
    elements, attlists = parse_dtd(DTD)
    defs, toplevel, other, conflicts, _ = parse_xsd(XSD)
    out = {}
    out["dtd_counts"] = {"elements": len(elements), "attlists": len(attlists)}
    out["xsd_counts"] = {"toplevel_elements": len(toplevel), "defs": len(defs), "non_element_toplevel": sorted(set(other)), "conflicting_local_defs": sorted(set(conflicts))}
    out["dtd_root_candidates"] = [e for e in elements if not any(e == c[0] for el in elements.values() for c in el["children"])]
    out["xsd_root_candidates"] = [e for e in toplevel if not any(e == c[0] for d in defs.values() for c in flat_children(d["children"]))]
    out["xsd_root_content"] = [(c[0],) + tuple(c[1:]) for c in flat_children(defs["CURRICULO-VITAE"]["children"])]
    out["xsd_root_attrs"] = defs["CURRICULO-VITAE"]["attrs"]
    out["dtd_root_attrs"] = attlists["CURRICULO-VITAE"]
    out["dtd_root_model"] = elements["CURRICULO-VITAE"]["model"]

    def dtd_descend(name, depth=0, maxd=2):
        e = elements.get(name)
        if not e:
            return ["%s%s (undeclared)" % ("  " * depth, name)]
        ats = attlists.get(name, {})
        s = ", ".join("%s[%s]" % (k, "R" if v["default"] == "#REQUIRED" else "o") for k, v in ats.items())
        lines = ["%s%s attrs=%s" % ("  " * depth, name, s)]
        if depth < maxd:
            for c in e["children"]:
                lines.extend(dtd_descend(c[0], depth + 1, maxd))
        return lines

    sec_report = {}
    for s in SECTIONS:
        sec_report[s] = {"dtd_model": elements[s]["model"], "dtd_children": [c[0] for c in elements[s]["children"]],
                         "xsd_children": [(c[0], c[1], c[2]) for c in flat_children(defs[s]["children"])],
                         "dtd_attrs": attlists.get(s, {}), "xsd_attrs": defs[s]["attrs"]}
    out["sections"] = sec_report

    # detailed record-level attribute diffs
    diffs = {}
    for s in SECTIONS:
        dkids = [c[0] for c in elements[s]["children"]]
        xkids = [c[0] for c in flat_children(defs[s]["children"])]
        for k in sorted(set(dkids) | set(xkids)):
            dat = {a: v for a, v in attlists.get(k, {}).items()}
            xat = defs.get(k, {}).get("attrs", {})
            dchildren = [c[0] for c in elements.get(k, {"children": []})["children"]]
            xchildren = [c[0] for c in flat_children(defs[k]["children"])] if k in defs else None
            diffs[k] = {
                "section": s,
                "in_dtd": k in elements, "in_xsd": k in defs,
                "dtd_only_attrs": sorted(set(dat) - set(xat)),
                "xsd_only_attrs": sorted(set(xat) - set(dat)),
                "common_attrs": len(set(dat) & set(xat)),
                "dtd_children": dchildren, "xsd_children": xchildren,
                "required_mismatch": sorted(a for a in set(dat) & set(xat) if (dat[a]["default"] == "#REQUIRED") != (xat[a]["use"] == "required")),
                "type_mismatch": sorted(a for a in set(dat) & set(xat) if (dat[a]["type"].startswith("ENUM")) != (str(xat[a]["type"]).startswith("ENUM"))),
            }
    out["record_diffs"] = diffs
    Path("/out/structure.json").write_text(json.dumps(out, indent=1, ensure_ascii=False, default=str), encoding="utf-8")

    # human trees
    tl = []
    for s in SECTIONS:
        tl.append("=== XSD " + s)
        tl.extend(xsd_tree(defs, s, 0, 3))
        tl.append("=== DTD " + s)
        tl.extend(dtd_descend(s, 0, 3))
    Path("/out/trees.txt").write_text("\n".join(tl), encoding="utf-8")
    print("ok")


if __name__ == "__main__":
    main()
