#!/usr/bin/env bash
# Checks for the orphan report and the literal rendering. No framework: each case runs a
# script against tests/fixtures/orphans.ttl and compares the output to what the fixture
# states must happen.
#
# Usage: tests/run.sh
set -u

here="$(cd "$(dirname "$0")" && pwd)"
scripts="$here/../skills/ontology-tools/scripts"
fixture="$here/fixtures/orphans.ttl"
failures=0

pass() { printf '  ok   %s\n' "$1"; }
fail() { printf '  FAIL %s\n' "$1"; failures=$((failures + 1)); }

expect_orphan() {
    local term="$1" want="$2" out="$3"
    if printf '%s' "$out" | grep -q "Orphan (never referenced): $term\$"; then
        [ "$want" = yes ] && pass "$term reported" || fail "$term reported, must not be"
    else
        [ "$want" = no ] && pass "$term not reported" || fail "$term not reported, must be"
    fi
}

echo "orphan report, no exclusions:"
out="$(uv run "$scripts/validate.py" "$fixture" --check-orphans 2>&1)"
expect_orphan ex:Cited          no  "$out"   # a triple points at it
expect_orphan ex:citedByQname   no  "$out"   # named by qname in a comment
expect_orphan ex:Inv_SomeRule   no  "$out"   # bare name, has an underscore
expect_orphan ex:HostedFields   no  "$out"   # bare name, two capitals
expect_orphan ex:Credit         yes "$out"   # the sentence uses the word, not the term
expect_orphan ex:SelfNamer      yes "$out"   # names only itself
expect_orphan ex:trueOrphan     yes "$out"
expect_orphan ex:excludedFact   yes "$out"   # no flag, so it reports

echo "orphan report, --orphan-exclude-type ex:Fact:"
out="$(uv run "$scripts/validate.py" "$fixture" --check-orphans --orphan-exclude-type ex:Fact 2>&1)"
expect_orphan ex:excludedFact   no  "$out"
expect_orphan ex:trueOrphan     no  "$out"   # also an ex:Fact
expect_orphan ex:Credit         yes "$out"   # not an ex:Fact, still reports
expect_orphan ex:SelfNamer      yes "$out"

echo "--orphan-exclude-type by bare local name:"
out="$(uv run "$scripts/validate.py" "$fixture" --check-orphans --orphan-exclude-type Fact 2>&1)"
expect_orphan ex:excludedFact   no  "$out"

echo "literal rendering:"
out="$(uv run "$scripts/lookup.py" ex:Bounded --closure --base-dir "$here" 2>&1)"
if printf '%s' "$out" | grep -q "owl:cardinality 1 \]"; then
    pass "an integer cardinality prints bare"
else
    fail "an integer cardinality prints bare — got: $(printf '%s' "$out" | grep cardinality)"
fi
if printf '%s' "$out" | grep -q "rdfs:label  'Bounded'"; then
    pass "a string label keeps its quotes"
else
    fail "a string label keeps its quotes"
fi

echo
if [ "$failures" -eq 0 ]; then
    echo "all checks pass"
else
    echo "$failures failed"
fi
exit $((failures > 0))
