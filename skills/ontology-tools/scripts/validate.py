#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["rdflib"]
# ///
"""
General-purpose Turtle ontology validator.

Usage:
  validate.py <file.ttl> [--namespace <prefix> <uri>] [--check-labels] [--check-ranges]
              [--check-orphans]

Always:
  - Parses the TTL and reports triple count (exit 1 on parse error)
  - Detects untyped named individuals (non-external subjects with no rdf:type)
  - Detects undeclared internal targets in rdfs:domain, rdfs:range, rdfs:subClassOf
  - Detects undeclared IRIs used inside OWL axioms (restrictions, lists) — typos that
    parse silently and disable the axiom they appear in

Optional checks (flags):
  --check-labels    Warn when rdfs:label is missing on any class or property
  --check-ranges    Warn when rdf:Property has no rdfs:range declared
  --check-orphans   Warn on declared terms never referenced by any other term
  --namespace p u   Report all terms in namespace u grouped by rdf:type
"""

import re
import sys
import argparse
import rdflib
from rdflib import RDF, RDFS, OWL


def parse_args():
    p = argparse.ArgumentParser(description="Validate a Turtle ontology file.")
    p.add_argument("path", help="Path to the .ttl file")
    p.add_argument("--check-labels", action="store_true", help="Warn on missing rdfs:label")
    p.add_argument("--check-ranges", action="store_true", help="Warn on properties missing rdfs:range")
    p.add_argument("--check-orphans", action="store_true", help="Warn on declared terms with no inbound references")
    p.add_argument(
        "--orphan-exclude-type",
        action="append",
        metavar="TYPE",
        help="Skip terms of this rdf:type in --check-orphans; repeatable. "
             "Takes a full URI, a qname, or a bare local name.",
    )
    p.add_argument("--namespace", nargs=2, metavar=("PREFIX", "URI"), help="Namespace to inspect")
    return p.parse_args()


def short(uri, g):
    try:
        return g.qname(uri)
    except Exception:
        return str(uri)


EXTERNAL_PREFIXES = {
    str(RDF),
    str(RDFS),
    str(OWL),
    "http://www.w3.org/2001/XMLSchema#",
    "https://www.w3.org/ns/activitystreams#",
    "https://w3id.org/security#",
}


def is_external(uri: rdflib.URIRef) -> bool:
    s = str(uri)
    return any(s.startswith(p) for p in EXTERNAL_PREFIXES)


def resolve_types(names, g: rdflib.Graph) -> set:
    """Each --orphan-exclude-type value, as a full URI, a qname, or a bare local name."""
    resolved = set()
    for name in names:
        if name.startswith(("http://", "https://")):
            resolved.add(rdflib.URIRef(name))
            continue
        if ":" in name:
            prefix, local = name.split(":", 1)
            match = next((ns for p, ns in g.namespaces() if p == prefix), None)
            if match is not None:
                resolved.add(rdflib.URIRef(str(match) + local))
                continue
        for subject in set(g.subjects()):
            if isinstance(subject, rdflib.URIRef) and str(subject).rsplit("#", 1)[-1].rsplit("/", 1)[-1] == name:
                resolved.add(subject)
    return resolved


def cited_in_prose(term: rdflib.URIRef, g: rdflib.Graph) -> bool:
    """
    True when another term's string literal names this one.

    An ontology cross-references in two ways: a triple, and a sentence inside an
    rdfs:comment. The second is a reference the graph does not record, so a term cited
    only that way reads as an orphan. Both written forms count: the qname
    (`payroc:replayWindow`) and the bare local name (`Inv_RecordBeforeCall`).

    The bare form is accepted only for a local name that no sentence would use as an
    ordinary word: one that has an underscore, or two or more capitals. Without that
    rule the local name `Credit` matches the sentence "A credit is a refill", and a
    real orphan then reads as cited.
    """
    qname = short(term, g)
    local = str(term).rsplit("#", 1)[-1].rsplit("/", 1)[-1]
    distinctive = "_" in local or sum(1 for c in local if c.isupper()) >= 2
    for subject, _, obj in g:
        if not isinstance(obj, rdflib.Literal) or subject == term:
            continue
        text = str(obj)
        if qname in text:
            return True
        if distinctive and re.search(rf"\b{re.escape(local)}\b", text):
            return True
    return False


def check(g: rdflib.Graph, args) -> int:
    warnings = 0

    ns = rdflib.Namespace(args.namespace[1]) if args.namespace else None

    # Collect named classes and properties (skip anonymous blank nodes)
    def uri_subjects(*type_uris):
        result = set()
        for t in type_uris:
            for s, _, _ in g.triples((None, RDF.type, t)):
                if isinstance(s, rdflib.URIRef):
                    result.add(s)
        return result

    classes = uri_subjects(RDFS.Class, OWL.Class)
    properties = uri_subjects(RDF.Property, OWL.ObjectProperty, OWL.DatatypeProperty)

    print(f"  Classes:    {len(classes)}")
    print(f"  Properties: {len(properties)}")

    # Untyped named individuals: non-external subjects with no rdf:type
    defined = set(g.subjects())
    for subj in sorted(defined, key=str):
        if not isinstance(subj, rdflib.URIRef):
            continue
        if is_external(subj):
            continue
        if not list(g.triples((subj, RDF.type, None))):
            print(f"  ⚠️  Untyped subject: {short(subj, g)}")
            warnings += 1

    # Undeclared internal targets in domain/range/subClassOf
    for pred in (RDFS.domain, RDFS.range, RDFS.subClassOf):
        for s, _, o in g.triples((None, pred, None)):
            if not isinstance(o, rdflib.URIRef):
                continue
            if is_external(o):
                continue
            if o not in defined:
                print(f"  ⚠️  {short(pred, g)} target not declared: {short(o, g)} (on {short(s, g)})")
                warnings += 1

    # Undeclared IRIs inside OWL axioms (restriction components + list members)
    # A typo here parses silently and disables the axiom without any error.
    declared = set(
        s for s, _, _ in g.triples((None, RDF.type, None))
        if isinstance(s, rdflib.URIRef)
    )
    axiom_preds = (
        OWL.onProperty, OWL.allValuesFrom, OWL.someValuesFrom,
        OWL.onClass, OWL.hasValue,
    )
    for pred in axiom_preds:
        for _, _, o in g.triples((None, pred, None)):
            if isinstance(o, rdflib.URIRef) and not is_external(o) and o not in declared:
                print(f"  ⚠️  Undeclared IRI in axiom: {short(o, g)} (as {short(pred, g)})")
                warnings += 1
    list_preds = (OWL.members, OWL.unionOf, OWL.intersectionOf)
    for pred in list_preds:
        for _, _, list_node in g.triples((None, pred, None)):
            if not isinstance(list_node, rdflib.BNode):
                continue
            try:
                for item in rdflib.collection.Collection(g, list_node):
                    if isinstance(item, rdflib.URIRef) and not is_external(item) and item not in declared:
                        print(f"  ⚠️  Undeclared IRI in list: {short(item, g)} (via {short(pred, g)})")
                        warnings += 1
            except Exception:
                pass

    # Missing labels (skip blank nodes — they can't have labels)
    if args.check_labels:
        for term in sorted(classes | properties, key=str):
            if not isinstance(term, rdflib.URIRef):
                continue
            if not list(g.triples((term, RDFS.label, None))):
                print(f"  ⚠️  No rdfs:label on {short(term, g)}")
                warnings += 1

    # Properties missing rdfs:range
    if args.check_ranges:
        for prop in sorted(properties, key=str):
            if not list(g.triples((prop, RDFS.range, None))):
                print(f"  ⚠️  No rdfs:range on {short(prop, g)}")
                warnings += 1

    # Orphaned terms: declared but never referenced by any other term
    if args.check_orphans:
        # Collect all IRIs that appear as objects or inside RDF lists
        referenced = set(o for _, _, o in g if isinstance(o, rdflib.URIRef))
        for pred in list_preds:
            for _, _, list_node in g.triples((None, pred, None)):
                if not isinstance(list_node, rdflib.BNode):
                    continue
                try:
                    for item in rdflib.collection.Collection(g, list_node):
                        if isinstance(item, rdflib.URIRef):
                            referenced.add(item)
                except Exception:
                    pass
        excluded_types = resolve_types(args.orphan_exclude_type or [], g)
        individuals = uri_subjects(OWL.NamedIndividual)
        for term in sorted(classes | properties | individuals, key=str):
            if is_external(term):
                continue
            if term in referenced:
                continue
            if excluded_types & set(g.objects(term, RDF.type)):
                continue
            if cited_in_prose(term, g):
                continue
            print(f"  ⚠️  Orphan (never referenced): {short(term, g)}")
            warnings += 1

    # Namespace inspection
    if ns:
        prefix = args.namespace[0]
        print(f"\n  Terms in {prefix}: namespace:")
        ns_terms = set(
            s for s in set(g.subjects())
            if isinstance(s, rdflib.URIRef) and str(s).startswith(str(ns))
        )
        by_type = {}
        for term in sorted(ns_terms, key=str):
            types = tuple(sorted(str(o).split("#")[-1] for _, _, o in g.triples((term, RDF.type, None))))
            by_type.setdefault(types or ("(untyped)",), []).append(short(term, g))
        for types, terms in sorted(by_type.items()):
            print(f"    [{', '.join(types)}]")
            for t in terms:
                print(f"      {t}")

    return warnings


def main():
    args = parse_args()
    print(f"Parsing {args.path} ...")
    g = rdflib.Graph()
    try:
        g.parse(args.path, format="turtle")
    except Exception as e:
        print(f"❌ Parse error: {e}")
        sys.exit(1)

    print(f"OK: {len(g)} triples\n")
    print("Checking:")
    warnings = check(g, args)

    if warnings:
        print(f"\n⚠️  {warnings} warning(s)")
    else:
        print("\n✅ No issues found")

    sys.exit(0)


if __name__ == "__main__":
    main()
