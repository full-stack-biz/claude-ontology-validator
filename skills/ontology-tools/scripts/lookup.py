#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["rdflib"]
# ///
"""
Look up an ontology term by ttl:// reference.

Usage:
  lookup.py ttl://domain.ttl/prefix:localName [--base-dir PATH]

Prints all triples where the term is the subject.
Exit 0 on found, 1 on error or not found.
"""

import sys
import re
import argparse
from pathlib import Path
import rdflib


def parse_ref(ref: str) -> tuple[str, str]:
    m = re.match(r"^ttl://([^/]+\.ttl)/(.+)$", ref)
    if not m:
        print(f"❌ Invalid ttl:// reference: {ref}")
        sys.exit(1)
    return m.group(1), m.group(2)


def find_ttl(filename: str, base: Path) -> Path:
    hits = list(base.rglob(filename))
    if not hits:
        print(f"❌ {filename} not found under {base}")
        sys.exit(1)
    return hits[0]


def resolve_prefixed(name: str, g: rdflib.Graph) -> rdflib.URIRef:
    prefix, local = name.split(":", 1)
    for p, ns in g.namespaces():
        if p == prefix:
            return rdflib.URIRef(str(ns) + local)
    print(f"❌ Prefix '{prefix}' not declared in ontology")
    sys.exit(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ref", help="ttl:// reference, e.g. ttl://domain.ttl/ns:Term")
    ap.add_argument("--base-dir", default=".", help="Root directory to search for the TTL file")
    args = ap.parse_args()

    filename, prefixed = parse_ref(args.ref)
    ttl_path = find_ttl(filename, Path(args.base_dir))

    g = rdflib.Graph()
    try:
        g.parse(ttl_path, format="turtle")
    except Exception as e:
        print(f"❌ Parse error: {e}")
        sys.exit(1)

    term = resolve_prefixed(prefixed, g)
    triples = list(g.triples((term, None, None)))

    if not triples:
        print(f"❌ No triples found for {prefixed}")
        sys.exit(1)

    print(f"# {prefixed}")
    for _, pred, obj in sorted(triples, key=lambda t: str(t[1])):
        try:
            p_s = g.qname(pred)
        except Exception:
            p_s = str(pred)
        if isinstance(obj, rdflib.URIRef):
            try:
                o_s = g.qname(obj)
            except Exception:
                o_s = str(obj)
        else:
            o_s = repr(str(obj))
        print(f"  {p_s}  {o_s}")


if __name__ == "__main__":
    main()
