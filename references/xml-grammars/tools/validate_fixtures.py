import hashlib
import json
import re
from pathlib import Path

from lxml import etree

G = Path("/g")
F = Path("/f")
DTD_PATH = G / "community-dtd" / "LMPLCurriculo.DTD"
XSD_PATH = G / "cnpq-official" / "xml_cvbase_src_main_resources_CurriculoLattes_12_09_2022.xsd"

# Schema parse: trusted local files only; no network, no entity resolution.
schema_parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False, huge_tree=False)
xsd_doc = etree.parse(str(XSD_PATH), schema_parser)
xsd = etree.XMLSchema(xsd_doc)
dtd = etree.DTD(str(DTD_PATH))
print("lxml", etree.LXML_VERSION, "libxml2", etree.LIBXML_VERSION)
print("DTD root-less element decls:", len(list(dtd.iterelements())), "attlists:", sum(len(list(e.iterattributes())) for e in dtd.iterelements()))

doc_parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False,
                             dtd_validation=False, attribute_defaults=False, huge_tree=False)
results = {}
for p in sorted(F.glob("*.xml")):
    data = p.read_bytes()
    r = {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data),
         "has_doctype": b"<!DOCTYPE" in data, "has_entity_decl": b"<!ENTITY" in data}
    doc = etree.fromstring(data, doc_parser)
    tree = etree.ElementTree(doc)
    r["root"] = doc.tag
    r["sections"] = {t: len(tree.xpath("//" + t)) for t in
                     ("FORMACAO-ACADEMICA-TITULACAO", "FORMACAO-COMPLEMENTAR", "PARTICIPACAO-EM-EVENTOS-CONGRESSOS")}
    r["section_parents"] = {t: sorted({e.getparent().tag for e in tree.xpath("//" + t)}) for t in r["sections"]}
    ok_x = xsd.validate(tree)
    r["xsd_valid"] = bool(ok_x)
    r["xsd_errors"] = [{"line": e.line, "msg": e.message} for e in xsd.error_log]
    ok_d = dtd.validate(tree)
    r["dtd_valid"] = bool(ok_d)
    r["dtd_errors"] = [{"line": e.line, "msg": e.message} for e in dtd.error_log]
    results[p.name] = r

# Attribute-level cross check against both grammars (independent of validity ordering):
x_attr = {}
for el in xsd_doc.getroot().iter("{http://www.w3.org/2001/XMLSchema}element"):
    pass
Path("/out/fixture_validation.json").write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")
for n, r in results.items():
    print("\n==", n, "doctype:", r["has_doctype"], "entity:", r["has_entity_decl"], "sha256", r["sha256"][:16])
    print("  sections", r["sections"], r["section_parents"])
    print("  XSD valid:", r["xsd_valid"], "errors:", len(r["xsd_errors"]))
    for e in r["xsd_errors"]:
        print("    L%s %s" % (e["line"], e["msg"][:230]))
    print("  DTD valid:", r["dtd_valid"], "errors:", len(r["dtd_errors"]))
    for e in r["dtd_errors"]:
        print("    L%s %s" % (e["line"], e["msg"][:230]))
