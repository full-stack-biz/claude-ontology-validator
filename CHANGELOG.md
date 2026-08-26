# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/full-stack-biz/ontology-tools/compare/v1.2.0...HEAD
[1.2.0]: https://github.com/full-stack-biz/ontology-tools/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/full-stack-biz/ontology-tools/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/full-stack-biz/ontology-tools/releases/tag/v1.0.0
