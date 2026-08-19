# Claude Ontology Validator

A Claude Code skill for validating implementation decisions and proposed changes against a [Turtle (.ttl)](https://www.w3.org/TR/turtle/) domain ontology. Parses the TTL with rdflib, checks structural axioms and named invariants, and reports each as PASS/FAIL with file:line evidence.

## What You Get

### Ontology Health Checks
Parse any `.ttl` file, verify syntax, count triples, and surface structural gaps—missing labels, missing ranges, undocumented invariants.

### Implementation Audits
Check code, schema, or architecture decisions against declared ontology axioms. Every check gets a verdict: `✅ PASS`, `❌ FAIL`, `⚠️ MISMATCH`, or `⚠️ ONTOLOGY GAP`.

### Named Invariant Enforcement
Named invariants (`*:Inv_*`) are extracted automatically and checked against the codebase with grep evidence.

### Namespace Inspection
List all terms in a given namespace prefix to audit coverage.

## Quick Start

### The Problem

Your project has a Turtle ontology that declares the domain model—classes, properties, invariants, cardinalities. Over time, code drifts from what the ontology says. Catching that drift manually is slow and error-prone.

### The Solution: Automatic Validation

With `claude-ontology-validator`, Claude checks the code against the ontology for you:

```
User: "Validate this PR against the ontology"

Claude (using ontology-validator):
→ Reads the .ttl file
→ Identifies relevant axioms and invariants
→ Greps the codebase for evidence
→ Reports each check as PASS/FAIL with file:line pointers

User gets: A structured report with an overall verdict
```

### Trigger Phrases

The skill activates when you ask Claude to:
- "Validate against the ontology"
- "Check domain invariants"
- "Does this violate the ontology?"
- "Ontology gap / ontology review"
- "Audit the domain model"

## Usage Scenarios

### Scenario 1: Validate a New Column
You're adding a database column and want to confirm it fits the declared domain.

```
me: "Does adding a `processed_at` timestamp column violate the ontology?"

Claude:
→ Reads ontology.ttl
→ Checks rdfs:range and cardinality restrictions for time-related properties
→ Reports PASS or FAIL with the relevant axioms
```

### Scenario 2: Audit the Ontology Itself
You edited the TTL and want to catch gaps before merging.

```
me: "Validate the ontology for completeness"

Claude:
→ Runs the validator script (syntax + triple count)
→ Checks for missing labels, comments, domain/range declarations
→ Lists every gap with its term URI
```

### Scenario 3: Pre-PR Invariant Check
Before opening a pull request, confirm no named invariants are violated.

```
me: "Ontology review for this PR"

Claude:
→ Reads all Inv_* instances from the TTL
→ Greps relevant source files for evidence
→ Returns a summary table with per-invariant verdicts
```

## Installation

### From GitHub
```bash
claude plugin install https://github.com/full-stack-biz/claude-ontology-validator --scope user
```

### From Marketplace
```bash
/plugin marketplace add full-stack-biz/claude-ontology-validator
```
```bash
/plugin install claude-ontology-validator@claude-ontology-validator
```

### Local Development
```bash
claude --plugin-dir /path/to/claude-ontology-validator
```

## Requirements

- **System:** Requires `uv` for running the Python validator script
- **Python:** 3.11 or higher
- **Dependencies:** `rdflib` (installed automatically by `uv`)

## How the Skill Works Internally

The validator script (`skills/ontology-validator/scripts/validate.py`):
- Parses the `.ttl` file with **rdflib**
- Reports triple count, syntax errors with line numbers
- Optionally checks `rdfs:label` coverage (`--check-labels`)
- Optionally checks `rdfs:range` declarations (`--check-ranges`)
- Accepts a `--namespace` flag to list all terms in a given prefix

Claude's skill instructions (`SKILL.md`) guide two workflows: keeping the ontology valid, and applying it to implementation decisions.

## Verdict Reference

| Verdict | Meaning | Fix goes in |
|---|---|---|
| ✅ PASS | Code matches ontology | — |
| ❌ FAIL | Code violates ontology | Code |
| ⚠️ MISMATCH | Ontology wrong about the code | Ontology |
| ⚠️ ONTOLOGY GAP | Concept exists in code, not in ontology | Ontology |

Overall: `✅ COMPLIANT` / `⚠️ PARTIAL` (gaps/mismatches only) / `❌ FAIL` (any violation).

## Version

**1.0.0** — Initial release.

## License

MIT

## Author

[full-stack-biz](https://github.com/full-stack-biz)

## Repository

https://github.com/full-stack-biz/claude-ontology-validator
