#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["rdflib"]
# ///
"""
Emit a Mermaid classDiagram from a Turtle ontology.

Usage:
  ttl2mermaid.py <file.ttl> [--root prefix:Class] [--prefix prefix] [--individuals]

Classes become nodes and rdfs:subClassOf becomes an inheritance edge. An object
property whose domain and range are both in the view becomes an association
labelled with the property. A datatype property becomes an attribute of its
domain class, and a union domain reaches every member of the union. A property
named by an owl:Restriction becomes an attribute too, with the bound the
restriction states — `1`, `0..1`, `0..0`, `1..*` or `only prefix:Class`.
Disjointness becomes a dashed link, from owl:disjointWith and from
owl:AllDisjointClasses. --individuals adds each named individual as a member of
the class it is typed with.

The whole file in one diagram is unreadable, so scope it with --root or
--prefix. Every term the scope excludes is reported on stderr, because a diagram
that drops a term without saying so reads as the whole domain.
"""

from __future__ import annotations

import argparse
import sys

from rdflib import OWL, RDF, RDFS, Graph, URIRef
from rdflib.term import Node

# Individuals of these classes are excluded unless --individuals is given: the
# invariants and the vendor facts outnumber the classes and connect to nothing.
NOISY_TYPES = {"Invariant", "VendorFact"}


def qname(graph: Graph, node: Node) -> str:
    """`wash:Payment` for a term of the graph, or the IRI when no prefix binds it."""
    try:
        prefix, _, local = graph.compute_qname(str(node))
    except (ValueError, KeyError):
        return str(node)
    return f"{prefix}:{local}" if prefix else local


def expand(graph: Graph, node: Node) -> set[Node]:
    """The classes a domain or a range names.

    `rdfs:domain wash:Payment` names one. `rdfs:domain [ owl:unionOf ( A B C ) ]`
    parses as a blank node, and reading it as one class drops the property from
    every member of the union — which is how `wash:amountCents` went missing.
    """
    members = list(graph.objects(node, OWL.unionOf))

    if not members:
        return {node}

    return {item for head in members for item in graph.items(head)}


def node_id(name: str) -> str:
    """Mermaid rejects a colon in a class name."""
    return name.replace(":", "_").replace("-", "_")


def classes_in_scope(graph: Graph, root: str | None, prefix: str | None) -> set[URIRef]:
    declared = {c for c in graph.subjects(RDF.type, OWL.Class) if isinstance(c, URIRef)}

    if root is not None:
        target = next((c for c in declared if qname(graph, c) == root), None)
        if target is None:
            sys.exit(f"No class named {root} is declared in the file.")
        scoped = {target}
        # Every subclass, transitively. The chain is short, so repeat until it settles.
        while True:
            grown = scoped | {
                c for c in declared for parent in graph.objects(c, RDFS.subClassOf) if parent in scoped
            }
            if grown == scoped:
                return grown
            scoped = grown

    if prefix is not None:
        return {c for c in declared if qname(graph, c).startswith(f"{prefix}:")}

    return declared


def restriction_members(graph: Graph, cls: URIRef) -> list[str]:
    """The properties a class names in its own restrictions, with the bound each states.

    This ontology writes most of its property assignments as `owl:Restriction`, not as
    `rdfs:domain`. `wash:Refund` requires `wash:idempotencyKey` that way, and a
    domain-only reading leaves the property off `wash:WalletRefund` entirely.
    """
    members = []

    for parent in graph.objects(cls, RDFS.subClassOf):
        prop = next(graph.objects(parent, OWL.onProperty), None)
        if prop is None:
            continue

        bound = ""
        for predicate, form in (
            (OWL.cardinality, "{}"),
            (OWL.minCardinality, "{}..*"),
            (OWL.maxCardinality, "0..{}"),
        ):
            value = next(graph.objects(parent, predicate), None)
            if value is not None:
                bound = form.format(int(value))

        for only in graph.objects(parent, OWL.allValuesFrom):
            bound = f"only {qname(graph, only)}" if isinstance(only, URIRef) else "only a restriction"

        members.append(f"{qname(graph, prop)} {bound}".strip())

    return members


def disjoint_pairs(graph: Graph, scope: set[URIRef]) -> list[tuple[URIRef, URIRef]]:
    """Every disjointness both ends of which are in the view.

    Written two ways in OWL: `owl:disjointWith` on the class, and an
    `owl:AllDisjointClasses` axiom with a list of members.
    """
    pairs = set()

    for left, right in graph.subject_objects(OWL.disjointWith):
        if left in scope and right in scope:
            pairs.add(tuple(sorted((left, right), key=str)))

    for axiom in graph.subjects(RDF.type, OWL.AllDisjointClasses):
        for head in graph.objects(axiom, OWL.members):
            listed = [m for m in graph.items(head) if m in scope]
            for index, left in enumerate(listed):
                for right in listed[index + 1 :]:
                    pairs.add(tuple(sorted((left, right), key=str)))

    return sorted(pairs, key=lambda pair: (str(pair[0]), str(pair[1])))


def render(graph: Graph, scope: set[URIRef], individuals: bool) -> list[str]:
    lines = ["```mermaid", "classDiagram"]
    names = {c: qname(graph, c) for c in scope}

    for cls in sorted(scope, key=lambda c: names[c]):
        members = []

        for prop in sorted(graph.subjects(RDF.type, OWL.DatatypeProperty), key=str):
            domains = {d for obj in graph.objects(prop, RDFS.domain) for d in expand(graph, obj)}
            if cls in domains:
                ranges = [qname(graph, r) for r in graph.objects(prop, RDFS.range)]
                members.append(f"{qname(graph, prop)} {ranges[0] if ranges else ''}".strip())

        stated = {m.split(" ")[0] for m in members}
        members.extend(m for m in restriction_members(graph, cls) if m.split(" ")[0] not in stated)

        if individuals:
            for member in sorted(graph.subjects(RDF.type, cls), key=str):
                members.append(f"{qname(graph, member)}()")

        lines.append(f"class {node_id(names[cls])}[\"{names[cls]}\"] {{")
        lines.extend(f"  {m}" for m in members)
        lines.append("}")

    for cls in sorted(scope, key=lambda c: names[c]):
        for parent in graph.objects(cls, RDFS.subClassOf):
            if parent in scope:
                lines.append(f"{node_id(names[parent])} <|-- {node_id(names[cls])}")

    for prop in sorted(graph.subjects(RDF.type, OWL.ObjectProperty), key=str):
        domains = {d for obj in graph.objects(prop, RDFS.domain) for d in expand(graph, obj)}
        ranges = {r for obj in graph.objects(prop, RDFS.range) for r in expand(graph, obj)}
        for domain in sorted(domains & scope, key=str):
            for rng in sorted(ranges & scope, key=str):
                lines.append(
                    f"{node_id(qname(graph, domain))} --> "
                    f"{node_id(qname(graph, rng))} : {qname(graph, prop)}"
                )

    for left, right in disjoint_pairs(graph, scope):
        lines.append(f"{node_id(names[left])} .. {node_id(names[right])} : disjoint")

    lines.append("```")
    return lines


def report_excluded(graph: Graph, scope: set[URIRef], individuals: bool) -> None:
    declared = {c for c in graph.subjects(RDF.type, OWL.Class) if isinstance(c, URIRef)}
    dropped = sorted(qname(graph, c) for c in declared - scope)
    if dropped:
        print(f"Classes outside this view: {', '.join(dropped)}", file=sys.stderr)
    if not individuals:
        noisy = sorted(
            qname(graph, c) for c in declared if qname(graph, c).split(":")[-1] in NOISY_TYPES
        )
        if noisy:
            print(
                f"Individuals are not drawn. Their types include: {', '.join(noisy)}. "
                "Pass --individuals to draw them.",
                file=sys.stderr,
            )

    # A property with one end outside the view is drawn nowhere, and a reader who
    # opens the diagram for `wash:Payment` would read it as having no state.
    crossing = set()
    for prop in graph.subjects(RDF.type, OWL.ObjectProperty):
        ends = {
            end
            for predicate in (RDFS.domain, RDFS.range)
            for obj in graph.objects(prop, predicate)
            for end in expand(graph, obj)
        }
        if ends & scope and not ends <= scope:
            crossing.add(qname(graph, prop))
    if crossing:
        print(f"Properties that leave this view: {', '.join(sorted(crossing))}", file=sys.stderr)

    # A restriction becomes a member with its bound. What the member cannot show is
    # the nested form: `allValuesFrom` a restriction rather than a class, and
    # `hasValue`. Name the classes that declare one, so the reader opens the file.
    nested = sorted(
        {
            qname(graph, cls)
            for cls in scope
            for parent in graph.objects(cls, RDFS.subClassOf)
            if any(not isinstance(v, URIRef) for v in graph.objects(parent, OWL.allValuesFrom))
            or any(True for _ in graph.objects(parent, OWL.hasValue))
        }
    )
    if nested:
        print(
            "A nested restriction is drawn as `only a restriction`. Read the axiom with "
            f"the ontology-tools skill for: {', '.join(nested)}",
            file=sys.stderr,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", help="the Turtle file to read")
    parser.add_argument("--root", help="draw this class and every subclass of it")
    parser.add_argument("--prefix", help="draw the classes of this prefix")
    parser.add_argument("--individuals", action="store_true", help="draw named individuals")
    args = parser.parse_args()

    graph = Graph()
    graph.parse(args.file, format="turtle")

    scope = classes_in_scope(graph, args.root, args.prefix)
    print("\n".join(render(graph, scope, args.individuals)))
    report_excluded(graph, scope, args.individuals)


if __name__ == "__main__":
    main()
