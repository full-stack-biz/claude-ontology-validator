---
name: ontology-tools
description: >-
  Turtle ontology toolbox: (1) validate — check syntax, labels, ranges, find
  gaps, fix TTL; (2) apply to decisions — check code/schema against declared
  axioms and invariants, report PASS/FAIL; (3) browse and search — list all
  classes, properties, and individuals without reading the raw TTL, search for
  terms by name or label; (4) resolve ttl:// references — look up a specific
  term by ttl://filename.ttl/prefix:LocalName and return its triples. Use when
  asked to: "validate ontology", "check against ontology", "does this violate
  the ontology", "ontology gap", "audit domain model", "apply ontology to this
  decision", "what's in this ontology", "list ontology terms", "find ontology
  concept for X", "look up ontology term", or "resolve ttl:// reference".
allowed_tools: ["Read", "Write", "Bash", "Grep"]
---

# Ontology Validator

Two distinct workflows. Pick the right one from context.

---

## Goal 1 — Keep the Ontology Valid

Use when the ontology file itself is being edited, extended, or audited for completeness.

### Step 1 — Parse and check structure

```bash
# Syntax + triple count + undeclared IRI check (always run first after any TTL edit)
uv run "$SKILLS_DIR/scripts/validate.py" path/to/ontology.ttl

# Also check labels, ranges, and orphaned terms
uv run "$SKILLS_DIR/scripts/validate.py" path/to/ontology.ttl \
  --check-labels --check-ranges --check-orphans

# Orphan check — skip terms of a given rdf:type (repeatable; full URI, qname, or bare local name)
uv run "$SKILLS_DIR/scripts/validate.py" path/to/ontology.ttl \
  --check-orphans --orphan-exclude-type owl:NamedIndividual

# Inspect all terms in a namespace
uv run "$SKILLS_DIR/scripts/validate.py" path/to/ontology.ttl \
  --namespace prefix https://example.org/ns#
```

If parse fails: fix the TTL before anything else. Parse errors are shown with line numbers.

### Step 2 — Read and audit the ontology

```
Read: path/to/ontology.ttl
```

Check for gaps:

| Gap type | What to look for |
|---|---|
| Missing `rdfs:label` | Every class, property, named individual should have one |
| Missing `rdfs:comment` | Every non-obvious term needs a comment explaining its semantics |
| Wrong `rdf:type` | Named individuals typed as the wrong class (e.g. an `allows` value typed as a Role) |
| Missing `rdfs:domain`/`rdfs:range` | Properties should declare both where it makes sense |
| Undocumented invariants | Constraints that exist in code but have no representation in the TTL |
| Spec references missing | If the ontology models a standard (AP, ForgeFed, etc.), comments should cite spec sections |
| Undeclared IRI in axiom | A typo inside a restriction or list creates a fresh IRI that parses and stays consistent but silently disables the axiom — reported by `validate.py` by default |

### Step 3 — Fix and re-validate

After every TTL edit:

```bash
uv run "$SKILLS_DIR/scripts/validate.py" path/to/ontology.ttl
```

Exit code 0 = syntactically valid. Re-read the edited section to confirm semantics are correct.

---

## Goal 2 — Apply the Ontology to Decisions

Use when evaluating proposed code, schema, architecture, or implementation choices against what the ontology declares.

### Step 1 — Read the ontology

```
Read: path/to/ontology.ttl
```

Parse three sections:
- **Named invariants** — `*:Inv_*` instances with `rdfs:comment`. Always check on domain-path changes.
- **Structural axioms** — `rdfs:subClassOf`, `owl:Restriction`, `rdfs:range`, `rdfs:domain`.
- **Type classifications** — named individuals typed as enumerations.

### Step 2 — Identify relevant axioms

| Proposed change | Axioms to check |
|---|---|
| New column / property | `rdfs:range`, `rdfs:domain`, cardinality restrictions |
| New FK / relation | Disjoint classes, `rdfs:range` (which type can it point to?) |
| New enum value | Type classification (is this a valid instance of the declared class?) |
| New code flow / ordering | Named invariants (`Inv_*`) that constrain sequencing |
| New entity type | `AllDisjointClasses`, subclass restrictions |

### Step 3 — Gather evidence

```bash
# Find uses of a concept in source
grep -rn "SomeConcept\|some_concept" src/ lib/ app/ 2>/dev/null

# Find column definitions
grep -rn "column_name" database/migrations/ schema/ 2>/dev/null

# Find enum/state assignments
grep -rn '"value"\|:value' lib/ app/ 2>/dev/null

# Trace code flow for ordering invariants
# Read the relevant service/handler file directly
```

### Step 4 — Report

One entry per axiom checked. Most-critical first.

```
### ns:Inv_SomeInvariant — Short label
Status: ✅ PASS
Evidence: grep finds no violations; constraint holds.

### ns:SomeProp rdfs:range ns:SomeClass
Status: ❌ FAIL
Evidence: app/models/foo.rb:42 — stores raw integer, ontology requires ns:SomeClass reference
Fix: Store a typed reference, not a bare integer.
```

End with a summary table and overall verdict:

```
| Axiom | Status |
|---|---|
| ns:Inv_Foo | ✅ PASS |
| ns:Bar rdfs:range | ❌ FAIL |
| ns:Baz cardinality | ⚠️ MISMATCH |
| ns:Missing coverage | ⚠️ ONTOLOGY GAP |

Overall: ❌ FAIL — ns:Bar range violated.
```

### Verdict types

| Verdict | Meaning | Fix goes in |
|---|---|---|
| ✅ PASS | Code matches ontology | — |
| ❌ FAIL | Code violates ontology | Code |
| ⚠️ MISMATCH | Ontology wrong about the code | Ontology |
| ⚠️ ONTOLOGY GAP | Concept exists in code, not in ontology | Ontology |

Overall: `✅ COMPLIANT` / `⚠️ PARTIAL` (gaps/mismatches only) / `❌ FAIL` (any violation).

---

## Standard Namespace Prefixes

Always use these exact URIs. Copy-paste the block below into every new TTL file:

```turtle
@prefix rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl:  <http://www.w3.org/2002/07/owl#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .
```

| Prefix | Correct URI | Common mistake |
|--------|-------------|----------------|
| `xsd:` | `http://www.w3.org/2001/XMLSchema#` | `2000/01/XMLSchema#` (wrong year) |
| `rdfs:` | `http://www.w3.org/2000/01/rdf-schema#` | `2001/rdf-schema#` |
| `owl:` | `http://www.w3.org/2002/07/owl#` | — |
| `rdf:` | `http://www.w3.org/1999/02/22-rdf-syntax-ns#` | — |

---

## Key Facts

- **Find the ontology**: `find . -name "*.ttl" | head` or check project CLAUDE.md
- **Named invariants**: all `*:Inv_*` instances — read their `rdfs:comment` for the exact rule
- **If ontology and CLAUDE.md prose conflict**: the ontology wins
- **MISMATCH** → fix the ontology; **GAP** → add an axiom; **FAIL** → fix the code
- After any TTL edit: always re-run the validator script before reporting done

---

## Browsing and Searching the Ontology

**Do not read the whole TTL file to understand its structure or find a term.** Use `list.py` instead.

Index mode — compact overview of all classes, properties (with domain/range), and named individuals:

```bash
uv run "$SKILLS_DIR/scripts/list.py" path/to/domain.ttl
```

Search mode — find terms by name or label, returns `ttl://` refs ready for `lookup.py`:

```bash
uv run "$SKILLS_DIR/scripts/list.py" path/to/domain.ttl <filter>
# e.g.
uv run "$SKILLS_DIR/scripts/list.py" docs/domain.ttl tenant
# → ttl://domain.ttl/wash:Tenant  # Tenant
# → ttl://domain.ttl/wash:hasTenant  # has tenant
# → ...
```

Exit 1 on file not found or parse error. Exit 0 with "No terms matching" message when filter finds nothing.

---

## Looking Up Terms (lookup.py)

Code comments use `ttl://filename.ttl/prefix:LocalName` to reference ontology items.
**Do not read the whole TTL file to resolve terms.** Use the lookup script instead.

**Single or multi-ref** — positional args, blank line between each result:

```bash
uv run "$SKILLS_DIR/scripts/lookup.py" wash:amountCents wash:Payment --base-dir path/to/project
```

**Bare names** (`prefix:Name`) auto-find the TTL when only one exists in `--base-dir`. Use full `ttl://` form when multiple TTL files are present.

**stdin** — pipe refs one per line (removes the shell loop, "Installed N packages" prints once):

```bash
grep -rho 'ttl://[^ ]*' app/ | sort -u | uv run "$SKILLS_DIR/scripts/lookup.py" - --base-dir .
```

**Dangling-ref check** — exit 1 lists any refs that failed to resolve. Grep finds refs, the tool resolves them; a non-zero exit means something in the code points nowhere.

**Closure** — assembles all constraints on a class: its own triples, inherited restrictions (transitive `rdfs:subClassOf` chain expanded), disjointness memberships, and every property that declares it as `rdfs:domain` or `rdfs:range`:

```bash
uv run "$SKILLS_DIR/scripts/lookup.py" wash:Payment --closure --base-dir path/to/project
```
