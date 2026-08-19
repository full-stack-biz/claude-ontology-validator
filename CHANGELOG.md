# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] - 2026-08-19

### Added
- Validate Turtle (.ttl) ontology syntax and triple count via rdflib
- Check `rdfs:label` and `rdfs:range` coverage with `--check-labels` / `--check-ranges`
- List all terms in a namespace prefix with `--namespace`
- Apply ontology to implementation decisions: PASS / FAIL / MISMATCH / ONTOLOGY GAP verdicts
- Named invariant (`*:Inv_*`) extraction and enforcement with grep evidence
- Skill triggers: "validate ontology", "check against ontology", "ontology gap", "audit domain model"
