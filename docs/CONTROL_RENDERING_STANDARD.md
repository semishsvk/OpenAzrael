# Control Rendering Standard

## Status

**MANDATORY**

All future OpenAzrael room control renders must use source-exact geometry, source-derived textures/UVs and two lighting modes generated from the same camera and gameplay state.

## Required paired outputs

### 1. ORIGINAL-1996

Purpose: visual fidelity to the original 1996 game.

Rules:
- Geometry must be the complete source-derived room geometry.
- Textures, UVs, legacy colorkey/alpha semantics and object visibility must be source-backed.
- Lighting must come only from recovered original-lighting data, original renderer behavior, captured/reference evidence, or a documented deterministic reconstruction backed by those sources.
- Do not invent missing lights, light colors, intensities, falloff, fog, emissive contribution or shadow behavior.
- If original lighting for a room is not yet sufficiently recovered, the output must be marked **ORIGINAL-LIGHTING-PENDING** rather than approximated.

### 2. NEUTRAL-QA

Purpose: defect detection.

Rules:
- Use the same source-exact room state and camera as ORIGINAL-1996.
- Use deliberately neutral, even inspection lighting/fullbright-style exposure so geometry, UV orientation, missing textures, alpha errors, flipped assets, clipping and missing objects are easy to see.
- Neutral lighting must not modify geometry, UVs, material identity, texture identity or gameplay state.
- It is a QA view and must never be presented as the original game's lighting.

## Camera rule

Where a production/source portal camera exists, prefer the exact runtime/source-backed camera:
`eye = portal centroid + normal * 120`, `forward = normal`.

For additional forensic cameras, the camera pose must be deterministic and documented.

## Render pair invariant

For a given control pair:
- same room geometry,
- same object visibility state,
- same camera pose/FOV,
- same textures and UVs,
- only the lighting/exposure model may differ.

## Validation

A control render is not valid if:
- any geometry is AI-generated, hand-invented or approximate;
- textures are regenerated rather than sourced;
- UV orientation is altered by the renderer without source evidence;
- missing original lighting is silently substituted with an artistic approximation;
- the ORIGINAL-1996 and NEUTRAL-QA images use different geometry or gameplay state.

This standard complements ADR-033/ADR-034 and the v122-v131 source-fidelity gates.
