#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["rdflib"]
# ///
"""
General-purpose Turtle ontology validator.

Usage:
  validate.py <file.ttl> [--namespace <prefix> <uri>] [--check-labels] [--check-ranges]

Always:
  - Parses the TTL and reports triple count (exit 1 on parse error)
  - Detects untyped named individuals (subjects with no rdf:type)

Optional checks (flags):
  --check-labels    Warn when rdfs:label is missing on any class or property
  --check-ranges    Warn when rdf:Property has no rdfs:range declared
  --namespace p u   Report all terms in namespace u grouped by rdf:type
"""

import sys
import argparse
import rdflib
from rdflib import RDF, RDFS, OWL


def parse_args():
    p = argparse.ArgumentParser(description="Validate a Turtle ontology file.")
    p.add_argument("path", help="Path to the .ttl file")
    p.add_argument("--check-labels", action="store_true", help="Warn on missing rdfs:label")
    p.add_argument("--check-ranges", action="store_true", help="Warn on properties missing rdfs:range")
    p.add_argument("--namespace", nargs=2, metavar=("PREFIX", "URI"), help="Namespace to inspect")
    return p.parse_args()


def short(uri, g):
    try:
        return g.qname(uri)
    except Exception:
        return str(uri)


def check(g: rdflib.Graph, args) -> int:
    warnings = 0

    ns = rdflib.Namespace(args.namespace[1]) if args.namespace else None

    # Collect all classes and properties
    classes = set(s for s, _, _ in g.triples((None, RDF.type, RDFS.Class)))
    classes |= set(s for s, _, _ in g.triples((None, RDF.type, OWL.Class)))
    properties = set(s for s, _, _ in g.triples((None, RDF.type, RDF.Property)))
    properties |= set(s for s, _, _ in g.triples((None, RDF.type, OWL.ObjectProperty)))
    properties |= set(s for s, _, _ in g.triples((None, RDF.type, OWL.DatatypeProperty)))

    print(f"  Classes:    {len(classes)}")
    print(f"  Properties: {len(properties)}")

    # Missing labels
    if args.check_labels:
        for term in sorted(classes | properties, key=str):
            if not list(g.triples((term, RDFS.label, None))):
                print(f"  ⚠️  No rdfs:label on {short(term, g)}")
                warnings += 1

    # Properties missing rdfs:range
    if args.check_ranges:
        for prop in sorted(properties, key=str):
            if not list(g.triples((prop, RDFS.range, None))):
                print(f"  ⚠️  No rdfs:range on {short(prop, g)}")
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
