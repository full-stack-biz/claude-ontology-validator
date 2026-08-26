# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.6.0] - 2026-08-27

### Added
- `validate.py --orphan-exclude-type TYPE`: exclude all terms of a given `rdf:type` from the orphan report; repeatable; accepts full URI, qname, or bare local name — use when a type's instances are terminal by design (vendor facts, named invariants)
- `tests/run.sh` + `tests/fixtures/orphans.ttl`: smoke tests for the orphan check; each fixture term declares its expected verdict and the script asserts the output matches

### Fixed
- `validate.py --check-orphans`: terms referenced only inside `rdfs:comment` prose are no longer flagged as orphans — qname (`payroc:replayWindow`) and distinctive bare local name (`Inv_RecordBeforeCall`, any name with `_` or ≥2 capitals) both count; plain words like `Credit` are not matched
- `lookup.py`: numeric and boolean literals print bare (`owl:cardinality 1`, not `'1'`); untyped string literals keep their quotes

## [1.5.0] - 2026-08-27

### Fixed
- `lookup.py`: blank-node objects now expand inline — `owl:Restriction` shows as `[ owl:onProperty … ; owl:cardinality N ]`; `owl:unionOf` as `( A | B )`; `owl:oneOf` as `{ a b }`; `owl:inverseOf` properties as `[ owl:inverseOf p ]`
- `lookup.py --closure`: disjointness now includes inherited memberships — if any ancestor class is a member of `owl:AllDisjointClasses`, its disjoint partners are reported with `(via AncestorClass)` tags
- `lookup.py`: trailing punctuation (`.,;:)]`) stripped from refs before resolving — fixes false dangling-ref errors when grep captures end-of-sentence citations

## [1.4.0] - 2026-08-27

### Added
- `lookup.py`: multiple refs as positional args; stdin mode (`-`); bare `prefix:Name` accepted when base-dir contains a single TTL; refs grouped with blank lines; exit 1 listing all unresolved refs (dangling-ref check for free)
- `lookup.py --closure`: assembles the full constraint picture for a class — its own triples, inherited restrictions via transitive `rdfs:subClassOf`, disjointness memberships, and every property with it as `rdfs:domain` / `rdfs:range`
- `validate.py`: default check for undeclared IRIs inside OWL axioms — `owl:onProperty`, `owl:allValuesFrom`, `owl:someValuesFrom`, `owl:onClass`, `owl:hasValue`, and items in `owl:members` / `owl:unionOf` / `owl:intersectionOf` lists; catches typos that parse silently and disable the axiom
- `validate.py --check-orphans`: reports declared classes, properties, and named individuals that are never referenced by any other term

## [1.3.0] - 2026-08-27

### Fixed
- `validate.py`: skip anonymous blank nodes when counting classes and properties — counts now match `list.py` and `--check-labels` no longer emits spurious `No rdfs:label on n0…` warnings for anonymous `owl:Class` expressions

## [1.2.0] - 2026-08-26

### Added
- `lookup.py` — resolve a `ttl://filename.ttl/prefix:LocalName` reference and return all triples for that subject; avoids loading the whole TTL to look up one term
- `list.py` — compact ontology index (classes with subClassOf, properties with domain/range, named individuals grouped by type); optional filter arg for term search returning `ttl://` refs
- Standard namespace prefixes section in SKILL.md with copy-paste block and common-mistake table
- Skill now covers browse/search and `ttl://` resolution in addition to validate and decision-apply

### Changed
- Renamed project and plugin from `claude-ontology-validator` to `ontology-tools`
- Renamed skill from `ontology-validator` to `ontology-tools`
- Updated frontmatter description to cover all four capabilities
- Added `Write` to `allowed_tools`

### Fixed
- `validate.py`: skip blank nodes in `--check-labels` check (anonymous classes cannot have labels)

## [1.1.0] - 2026-08-19

### Added
- Detect untyped named individuals (non-external subjects with no `rdf:type`)
- Detect undeclared internal targets in `rdfs:domain`, `rdfs:range`, `rdfs:subClassOf`

## [1.0.0] - 2026-08-19

### Added
- Validate Turtle (.ttl) ontology syntax and triple count via rdflib
- Check `rdfs:label` and `rdfs:range` coverage with `--check-labels` / `--check-ranges`
- List all terms in a namespace prefix with `--namespace`
- Apply ontology to implementation decisions: PASS / FAIL / MISMATCH / ONTOLOGY GAP verdicts
- Named invariant (`*:Inv_*`) extraction and enforcement with grep evidence
- Skill triggers: "validate ontology", "check against ontology", "ontology gap", "audit domain model"

[Unreleased]: https://github.com/full-stack-biz/ontology-tools/compare/v1.6.0...HEAD
[1.6.0]: https://github.com/full-stack-biz/ontology-tools/compare/v1.5.0...v1.6.0
[1.5.0]: https://github.com/full-stack-biz/ontology-tools/compare/v1.4.0...v1.5.0
[1.4.0]: https://github.com/full-stack-biz/ontology-tools/compare/v1.3.0...v1.4.0
[1.3.0]: https://github.com/full-stack-biz/ontology-tools/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/full-stack-biz/ontology-tools/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/full-stack-biz/ontology-tools/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/full-stack-biz/ontology-tools/releases/tag/v1.0.0
