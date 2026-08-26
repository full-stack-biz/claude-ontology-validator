#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["rdflib"]
# ///
"""
Print a compact index of a Turtle ontology.

Usage:
  list.py <file.ttl> [filter]

Without filter: prints all classes, properties (with domain/range), and named
individuals grouped by type — one screen, no RDF syntax.

With filter: restricts output to terms whose local name or rdfs:label contains
the filter string (case-insensitive). Each matching term is shown with its
ttl:// reference so it can be passed directly to lookup.py.
"""

import sys
import re
import argparse
from pathlib import Path
import rdflib
from rdflib import RDF, RDFS, OWL

# Normalize XSD namespace variants (2000/01, 2001, etc.) to xsd:
_XSD_RE = re.compile(r"^http://www\.w3\.org/200\d(?:/\d+)?/XMLSchema#")


def short(uri, g):
    s = str(uri)
    m = _XSD_RE.match(s)
    if m:
        return f"xsd:{s[m.end():]}"
    best_len = 0
    candidates = []
    for p, ns in g.namespaces():
        ns_s = str(ns)
        if not s.startswith(ns_s):
            continue
        if len(ns_s) > best_len:
            best_len = len(ns_s)
            candidates = [(p, ns_s)]
        elif len(ns_s) == best_len:
            candidates.append((p, ns_s))
    if not candidates:
        return s
    # Prefer the prefix without a trailing digit (xsd over xsd1)
    candidates.sort(key=lambda x: (x[0][-1].isdigit() if x[0] else True, x[0]))
    prefix, ns_s = candidates[0]
    if not prefix or prefix[0].isdigit():
        return s
    return f"{prefix}:{s[best_len:]}"


def local(uri: rdflib.URIRef) -> str:
    s = str(uri)
    return s.split("#")[-1].split("/")[-1]


def label(uri, g) -> str:
    for _, _, o in g.triples((uri, RDFS.label, None)):
        return str(o)
    return ""


def ttl_ref(filename: str, uri, g) -> str:
    return f"ttl://{filename}/{short(uri, g)}"


def matches(uri, g, f: str) -> bool:
    f = f.lower()
    return f in local(uri).lower() or f in label(uri, g).lower()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", help="Path to the .ttl file")
    ap.add_argument("filter", nargs="?", default=None, help="Case-insensitive substring filter on local name or label")
    args = ap.parse_args()

    path = Path(args.path)
    if not path.exists():
        print(f"❌ File not found: {path}")
        sys.exit(1)
    g = rdflib.Graph()
    try:
        g.parse(path, format="turtle")
    except Exception as e:
        print(f"❌ Parse error: {e}")
        sys.exit(1)

    filename = path.name
    filt = args.filter

    def uri_subjects(*type_uris):
        result = set()
        for t in type_uris:
            for s, _, _ in g.triples((None, RDF.type, t)):
                if isinstance(s, rdflib.URIRef):
                    result.add(s)
        return sorted(result, key=str)

    classes = uri_subjects(RDFS.Class, OWL.Class)
    properties = uri_subjects(RDF.Property, OWL.ObjectProperty, OWL.DatatypeProperty, OWL.AnnotationProperty)
    individuals = uri_subjects(OWL.NamedIndividual)

    if filt:
        # Search mode: show matching terms with ttl:// refs
        hits = []
        for term in classes + properties + individuals:
            if matches(term, g, filt):
                hits.append(term)
        if not hits:
            print(f"No terms matching '{filt}'")
            sys.exit(0)
        for term in hits:
            ref = ttl_ref(filename, term, g)
            lbl = label(term, g)
            suffix = f"  # {lbl}" if lbl else ""
            print(f"{ref}{suffix}")
        sys.exit(0)

    # Index mode
    def _domain_range(prop):
        parts = []
        for _, _, o in g.triples((prop, RDFS.domain, None)):
            if isinstance(o, rdflib.URIRef):
                parts.append(f"domain:{short(o, g)}")
        for _, _, o in g.triples((prop, RDFS.range, None)):
            if isinstance(o, rdflib.URIRef):
                parts.append(f"range:{short(o, g)}")
        return "  " + "  ".join(parts) if parts else ""

    def _parents(cls):
        parents = [short(o, g) for _, _, o in g.triples((cls, RDFS.subClassOf, None))
                   if isinstance(o, rdflib.URIRef)]
        return f"  subClassOf: {', '.join(parents)}" if parents else ""

    def _lbl(term):
        lbl = label(term, g)
        return f'  "{lbl}"' if lbl else ""

    if classes:
        print(f"# Classes ({len(classes)})")
        for c in classes:
            print(f"  {short(c, g)}{_lbl(c)}{_parents(c)}")

    if properties:
        print(f"\n# Properties ({len(properties)})")
        for p in properties:
            print(f"  {short(p, g)}{_lbl(p)}{_domain_range(p)}")

    if individuals:
        # Group by type (excluding owl:NamedIndividual)
        by_type: dict[str, list] = {}
        for ind in individuals:
            types = [short(o, g) for _, _, o in g.triples((ind, RDF.type, None))
                     if str(o) != str(OWL.NamedIndividual)]
            key = ", ".join(sorted(types)) if types else "(untyped)"
            by_type.setdefault(key, []).append(ind)

        print(f"\n# Named Individuals ({len(individuals)})")
        for type_label_str, inds in sorted(by_type.items()):
            print(f"  [{type_label_str}]")
            for ind in inds:
                print(f"    {short(ind, g)}{_lbl(ind)}")


if __name__ == "__main__":
    main()
