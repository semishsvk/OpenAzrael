# PUZZLES file-I/O direct-call census — v103

## Source-safe retained summary

v103 established the bounded census that v104 later classified exhaustively. The
bound demo executable contains **47 direct call sites** to the audited standard
`fopen` wrapper class used by the v103/v104 investigation.

The complete raw disassembly/xref working set is reproducible forensic evidence
and is not retained in Git. The source-safe invariant carried forward is:

- audited class: direct calls to the standard stdio `fopen` path;
- direct call sites in the bounded census: **47**;
- v103 produced the candidate set consumed by v104;
- v103 alone did not identify a PUZZLES.DAT loader.

## Relationship to v104/v105

v104 classifies all 47/47 direct `fopen` call sites and leaves **0** plausible
direct PUZZLES.DAT candidates. v105 extends the negative search to alternative
direct-open mechanisms. These are bounded negative results, not proof that
PUZZLES.DAT is unused.

## Evidence boundary

Indirect calls, computed routing, custom abstractions, container/resource
systems and other non-audited access paths remain outside this direct-call
census. PUZZLES runtime loader identity therefore remains **HOLD**.

Provenance: compact reconstruction from the retained canonical v104
classification and v106 closure notes; no raw commercial-derived bytes are
included.
