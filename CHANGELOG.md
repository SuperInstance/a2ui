# Changelog

All notable changes to A2UI are documented here. Versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Fixed
- **Form `required` flag now propagates from `Field.required` to `InterfaceComponent.required`.** Previously, the `_build_form` builder dropped the flag, so the HTML output never emitted the `required` attribute and the Markdown form table marked every input as required. `HTMLRenderer._render_input` now emits `required` for inputs where the field was declared `required=True`; `MarkdownRenderer._render_form` now reads `c.required` instead of `c.field` truthiness. Three regression tests added. Note: `InterfaceComponent.to_dict()` now includes `"required": true` when set.
- **Form inputs now have proper `<label for="…">` linkage to `<input id="…">`.** The label previously had no `for` attribute and the input had no `id`, so screen readers couldn't associate them. Accessibility improvement.

### Docs
- New `docs/ARCHITECTURE.md` — the layer model, the whistle metaphor, three pluggable boundaries, design choices.
- New `docs/API.md` — every public symbol documented with attributes and signatures.
- New `docs/EXAMPLES.md` — descriptions of the three runnable examples plus a "build your own" template.
- New `docs/CONTRIBUTING.md` — quickstart, project layout, conventions for adding field types / view types / intent keywords / renderers, testing policy, release checklist.
- New `CHANGELOG.md` (this file).
- Two new runnable examples: `examples/issue_tracker.py` (non-fishing domain) and `examples/custom_renderer.py` (subclassing `BaseRenderer`).
- README updated to link the new docs.

## [0.1.0] - 2026-07-20

### Added
- Initial public release.
- `AdaptiveInterface` — main entry point.
- `Schema`, `Entity`, `Field` with `FieldType` (`TEXT`, `NUMBER`, `DATE`, `ENUM`, `REFERENCE`) and `ViewType` (`LIST`, `DETAIL`, `FORM`, `CHART`, `DASHBOARD`).
- `parse_intent` — keyword-based natural-language intent parser with no NLP dependencies.
- `InterfaceSpec` / `InterfaceComponent` — format-agnostic intermediate representation.
- Three renderers: `HTMLRenderer` (LCARS-styled, inline CSS), `MarkdownRenderer` (tables + bold), `JSONRenderer`.
- 58-test pytest suite.
- `examples/vessel_manifest.py` end-to-end demo.
- MIT licensed.

---

## Versioning Conventions

- **Bug fixes** that don't change behaviour for existing inputs go in a **patch** (0.1.0 → 0.1.1).
- **New features** that add optional behaviour (new `FieldType`, new renderer, new intent keyword) go in a **minor** (0.1.0 → 0.2.0).
- **Breaking changes** to public API (`AdaptiveInterface.render` signature, enum values, schema dataclass field removal) bump the **major**.

## How to Read This File

- **Added** for new features.
- **Changed** for behaviour changes to existing features.
- **Fixed** for bug fixes.
- **Removed** for retiring old API.
- **Deprecated** for soft removals, leaving a path forward.
- **Docs** for documentation-only changes.
