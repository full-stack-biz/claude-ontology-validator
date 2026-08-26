#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["rdflib"]
# ///
"""
Look up one or more ontology terms.

Usage:
  lookup.py [--base-dir PATH] [--closure] ref [ref ...]
  lookup.py [--base-dir PATH] [--closure] -   # read refs from stdin, one per line

ref formats:
  ttl://filename.ttl/prefix:LocalName     explicit file + term
  prefix:LocalName                         bare name (auto-finds TTL when unique in base-dir)

Output: all triples for each subject, grouped with blank lines between refs.
Exit 1 if any ref fails, listing the unresolved ones at the end.

--closure: also shows inherited restrictions (via rdfs:subClassOf chain), disjointness
           memberships, and every property that declares this class as domain or range.
"""

import sys
import re
import argparse
from pathlib import Path
import rdflib
from rdflib import RDF, RDFS, OWL

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
    candidates.sort(key=lambda x: (x[0][-1].isdigit() if x[0] else True, x[0]))
    prefix, ns_s = candidates[0]
    if not prefix or prefix[0].isdigit():
        return s
    return f"{prefix}:{s[best_len:]}"


_TRAILING_PUNCT = re.compile(r"[.,;:)\]]+$")


def parse_ref(ref: str) -> tuple[str | None, str] | None:
    """(filename_or_None, prefixed_name), or None if unparseable."""
    m = re.match(r"^ttl://([^/]+\.ttl)/(.+)$", ref)
    if m:
        local = _TRAILING_PUNCT.sub("", m.group(2))
        return m.group(1), local
    # strip before testing bare name too
    ref = _TRAILING_PUNCT.sub("", ref)
    if re.match(r"^[A-Za-z][A-Za-z0-9_-]*:[^\s/]+$", ref) and ref.count(":") == 1:
        return None, ref
    return None


def find_ttl(filename: str | None, base: Path) -> tuple[Path | None, str | None]:
    if filename:
        hits = list(base.rglob(filename))
        return (hits[0], None) if hits else (None, f"❌ {filename} not found under {base}")
    hits = list(base.rglob("*.ttl"))
    if not hits:
        return None, f"❌ No TTL files found under {base}"
    if len(hits) > 1:
        return None, f"❌ Multiple TTL files — use ttl://filename.ttl/prefix:Name"
    return hits[0], None


def load_graph(path: Path, cache: dict) -> tuple[rdflib.Graph | None, str | None]:
    if path in cache:
        return cache[path], None
    g = rdflib.Graph()
    try:
        g.parse(path, format="turtle")
    except Exception as e:
        return None, f"❌ Parse error: {e}"
    cache[path] = g
    return g, None


def resolve_term(prefixed: str, g: rdflib.Graph) -> rdflib.URIRef | None:
    prefix, local = prefixed.split(":", 1)
    for p, ns in g.namespaces():
        if p == prefix:
            return rdflib.URIRef(str(ns) + local)
    return None


def fmt_obj(obj, g) -> str:
    if isinstance(obj, rdflib.URIRef):
        return short(obj, g)
    if isinstance(obj, rdflib.BNode):
        return fmt_blank_node(obj, g)  # expanded below, after format_restriction
    return repr(str(obj))


def print_triples(triples, g):
    for _, pred, obj in sorted(triples, key=lambda t: str(t[1])):
        print(f"  {short(pred, g)}  {fmt_obj(obj, g)}")


def superclasses(term: rdflib.URIRef, g: rdflib.Graph) -> list[rdflib.URIRef]:
    visited, queue = [], [term]
    while queue:
        c = queue.pop()
        for _, _, sup in g.triples((c, RDFS.subClassOf, None)):
            if isinstance(sup, rdflib.URIRef) and sup not in visited:
                visited.append(sup)
                queue.append(sup)
    return visited


def format_restriction(bn: rdflib.BNode, g: rdflib.Graph) -> str:
    parts = []
    on_prop = next((o for _, _, o in g.triples((bn, OWL.onProperty, None))), None)
    if on_prop:
        parts.append(f"owl:onProperty {fmt_obj(on_prop, g)}")
    for rp in (OWL.allValuesFrom, OWL.someValuesFrom, OWL.onClass, OWL.hasValue,
               OWL.minCardinality, OWL.maxCardinality, OWL.cardinality,
               OWL.minQualifiedCardinality, OWL.maxQualifiedCardinality):
        for _, _, rv in g.triples((bn, rp, None)):
            parts.append(f"{short(rp, g)} {fmt_obj(rv, g)}")
    return "[ " + " ; ".join(parts) + " ]" if parts else f"_:{bn}"


def fmt_blank_node(bn: rdflib.BNode, g: rdflib.Graph) -> str:
    """Expand a blank node to a readable inline expression."""
    inv = next((o for _, _, o in g.triples((bn, OWL.inverseOf, None))), None)
    if inv is not None:
        return f"[ owl:inverseOf {fmt_obj(inv, g)} ]"
    if next(g.triples((bn, OWL.onProperty, None)), None):
        return format_restriction(bn, g)
    union_node = next((o for _, _, o in g.triples((bn, OWL.unionOf, None))), None)
    if union_node is not None:
        try:
            items = list(rdflib.collection.Collection(g, union_node))
            return "( " + " | ".join(fmt_obj(i, g) for i in items) + " )"
        except Exception:
            pass
    one_node = next((o for _, _, o in g.triples((bn, OWL.oneOf, None))), None)
    if one_node is not None:
        try:
            items = list(rdflib.collection.Collection(g, one_node))
            return "{ " + " ".join(fmt_obj(i, g) for i in items) + " }"
        except Exception:
            pass
    return f"_:{bn}"


def print_closure(term: rdflib.URIRef, g: rdflib.Graph):
    sups = superclasses(term, g)
    if sups:
        print("  # inherited via rdfs:subClassOf")
        for sup in sups:
            for _, _, obj in g.triples((sup, RDFS.subClassOf, None)):
                if isinstance(obj, rdflib.BNode):
                    print(f"    (from {short(sup, g)}) {format_restriction(obj, g)}")

    # Disjointness — check term and all ancestors (Bug B fix)
    # partner_via: partner label -> set of ancestor labels it arrives through (empty = direct)
    partner_via: dict[str, set[str]] = {}
    for subj in g.subjects(RDF.type, OWL.AllDisjointClasses):
        members_node = next((o for _, _, o in g.triples((subj, OWL.members, None))), None)
        if not members_node:
            continue
        try:
            members = list(rdflib.collection.Collection(g, members_node))
        except Exception:
            continue
        if term in members:
            for m in members:
                if m != term:
                    partner_via.setdefault(fmt_obj(m, g), set())
        else:
            for sup in sups:
                if sup in members:
                    via = short(sup, g)
                    for m in members:
                        if m != sup:
                            partner_via.setdefault(fmt_obj(m, g), set()).add(via)
    for _, _, other in g.triples((term, OWL.disjointWith, None)):
        partner_via.setdefault(fmt_obj(other, g), set())
    for other, _, _ in g.triples((None, OWL.disjointWith, term)):
        partner_via.setdefault(fmt_obj(other, g), set())
    if partner_via:
        print("  # disjoint with")
        for partner, vias in sorted(partner_via.items()):
            suffix = f"  (via {', '.join(sorted(vias))})" if vias else ""
            print(f"    {partner}{suffix}")

    # Domain / range uses
    as_domain = sorted([s for s, _, _ in g.triples((None, RDFS.domain, term))
                        if isinstance(s, rdflib.URIRef)], key=str)
    as_range = sorted([s for s, _, _ in g.triples((None, RDFS.range, term))
                       if isinstance(s, rdflib.URIRef)], key=str)
    if as_domain:
        print("  # properties with this class as domain")
        for p in as_domain:
            print(f"    {short(p, g)}")
    if as_range:
        print("  # properties with this class as range")
        for p in as_range:
            print(f"    {short(p, g)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("refs", nargs="+", help="refs or - for stdin")
    ap.add_argument("--base-dir", default=".", help="Root to search for TTL files")
    ap.add_argument("--closure", action="store_true",
                    help="Show inherited restrictions, disjointness, and domain/range uses")
    args = ap.parse_args()

    base = Path(args.base_dir)
    refs = [ln.strip() for ln in sys.stdin if ln.strip()] if args.refs == ["-"] else args.refs

    graph_cache: dict[Path, rdflib.Graph] = {}
    failed: list[str] = []

    for i, ref in enumerate(refs):
        if i > 0:
            print()

        parsed = parse_ref(ref)
        if parsed is None:
            print(f"# {ref}\n❌ Invalid ref (expected ttl://file.ttl/prefix:Name or prefix:Name)")
            failed.append(ref)
            continue

        filename, prefixed = parsed
        ttl_path, err = find_ttl(filename, base)
        if err:
            print(f"# {ref}\n{err}")
            failed.append(ref)
            continue

        g, err = load_graph(ttl_path, graph_cache)
        if err:
            print(f"# {ref}\n{err}")
            failed.append(ref)
            continue

        term = resolve_term(prefixed, g)
        if term is None:
            print(f"# {prefixed}\n❌ Prefix '{prefixed.split(':')[0]}' not declared in ontology")
            failed.append(ref)
            continue

        triples = list(g.triples((term, None, None)))
        print(f"# {prefixed}")
        if not triples:
            print(f"❌ No triples found for {prefixed}")
            failed.append(ref)
        else:
            print_triples(triples, g)
            if args.closure:
                print_closure(term, g)

    if failed:
        print(f"\n❌ Unresolved: {', '.join(failed)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
