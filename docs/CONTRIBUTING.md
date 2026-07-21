# Contributing to A2UI

A2UI is small on purpose. The whole library is ~600 lines of Python split across four files. That size is a feature: it's easy to read end-to-end and easy to extend. This guide shows you how to extend it without breaking the design.

---

## Quickstart

```bash
git clone https://github.com/SuperInstance/a2ui.git
cd a2ui
python -m venv .venv
source .venv/bin/activate   # or: uv venv .venv && source .venv/bin/activate
pip install -e ".[dev]"    # or: uv pip install -e ".[dev]"
pytest                     # runs 60+ tests, <1s
```

Edit code. Add tests. Run tests.

```bash
pytest                                       # full suite
pytest -k TestIntentParsing                  # one class
pytest tests/test_a2ui.py::TestSchema::test_x # one test
pytest --cov=a2ui --cov-report=term-missing   # with coverage
```

---

## Project Layout

```
a2ui/
├── src/a2ui/
│   ├── __init__.py        # public entrypoint — exposes AdaptiveInterface
│   ├── schema.py          # Schema / Entity / Field / FieldType / ViewType
│   ├── intent.py          # Intent / Filter / Sort + parse_intent()
│   ├── interface.py       # InterfaceSpec / InterfaceComponent
│   └── renderers.py       # HTMLRenderer / MarkdownRenderer / JSONRenderer / BaseRenderer
├── tests/test_a2ui.py     # full pytest suite
├── examples/              # runnable end-to-end demos
├── docs/                  # ARCHITECTURE / API / EXAMPLES / CONTRIBUTING
├── pyproject.toml         # packaging + pytest config
└── README.md              # the public face
```

The four source files map cleanly to the four architecture layers. When in doubt, find the layer your change lives in, edit that file, and add tests next to it.

---

## The Contract

Every public symbol is what it says it is. Look at the dataclasses in `interface.py` — `InterfaceComponent` only has fields that are explicitly useful. Don't add fields speculatively. If you need something new, add it as an optional field with a sensible default.

Same for `Intent` — keep its surface area stable. If you need to attach something to an intent, consider putting it on a subclass or in a side-dict.

---

## How to Add a `FieldType`

1. Add a value to the `FieldType` enum in `schema.py`.
2. Update `AdaptiveInterface._input_type_for()` (`__init__.py`) to map it to an HTML input type or `None`.
3. Optionally update `HTMLRenderer._render_input()` and `MarkdownRenderer._render_form()` if the new type needs special rendering.
4. Add a `test_*` case in `tests/test_a2ui.py::TestSchema`.

The simplest: a new HTML input type that round-trips through the existing path. The richer case: a field that needs custom JS (e.g. a JSON schema picker). For the latter, also document the expected `data-*` attributes on the rendered `<input>`.

---

## How to Add a `ViewType`

1. Add a value to the `ViewType` enum in `schema.py`.
2. Implement a `_build_*` method on `AdaptiveInterface` (`__init__.py`).
3. Wire it into `AdaptiveInterface._build_spec()` based on the parsed `intent.action` or `intent.view_hint`.
4. Add a `render_*` branch to each renderer that supports this view type. New renderers can skip view types they don't yet handle.
5. Add tests.

A new view type that doesn't have a renderer should still build a spec — renderers can fall back to LIST or display "unsupported" gracefully.

---

## How to Add an Intent Keyword

1. Edit `_ACTION_KEYWORDS` in `intent.py`.
2. Add a regex to one of the patterns (`_COMP_RE`, `_EQ_RE`, `_SORT_RE`, `_SORT_RE_ALT`) if it's a filter or sort syntax.
3. Add tests under `TestIntentParsing`.
4. Update the action-keyword table in `README.md` and `docs/API.md` so they stay in sync.

Be conservative with regex. The current patterns are simple by design. If your domain requires richer grammar, prefer writing a domain-specific `parse_intent` and passing the resulting `Intent` directly to `ai.render_intent()`.

---

## How to Add a Renderer

```python
from a2ui.renderers import BaseRenderer
from a2ui.interface import InterfaceSpec

class MyRenderer(BaseRenderer):
    def render(self, spec: InterfaceSpec) -> str:
        # walk spec.components, switch on spec.view_type, return a string
        ...
```

Treat `spec.components` as opaque except for the documented `component_type` values and the relevant fields per type (see [`ARCHITECTURE.md`](ARCHITECTURE.md) §6).

If you want your renderer to be reachable via `AdaptiveInterface.to_<format>(intent)`, that's a deliberate API surface — open an issue first.

---

## Coding Conventions

- **Type hints** on public functions (`def foo(x: int) -> str:`). Internal helpers can be untyped for brevity.
- **Dataclasses** for state. No `__init__` overrides unless you really need the validation; use `__post_init__`.
- **`str` Enum subclasses** when JSON round-trip matters (`FieldType`, `ViewType`).
- **`from __future__ import annotations`** at the top of every source file for forward-reference convenience.
- **Imports go to `a2ui`'s public API only.** Internal modules (`a2ui.intent`) can be imported directly only when crossing layer boundaries.
- **Single-line docstring for one-liners.** Multi-line for non-trivial functions. Public API gets a docstring that explains why, not just what.

The codebase intentionally uses **f-strings** rather than a templating engine — output is small, LCARS HTML is fully inline, and f-strings keep the audit surface tiny.

---

## Testing Policy

- All new code has tests.
- Regex changes in `intent.py` should include **positive and negative** tests (a string that should match, a string that should not).
- Renderer changes should include an **escape test** if user input could ever hit HTML — there is already a precedent in `TestRenderers::test_html_escapes`.
- Bug fixes get a regression test that fails on the old code.

The full suite runs in well under a second on a laptop. Keep it that way.

---

## Commit Messages

Imperative mood, present tense. Mention the layer:

```
intent: support "at most N" comparison
schema: add Field.reference validation
renderers: escape enum option labels
docs: link ARCHITECTURE from README
tests: regression for required-flag propagation
```

When committing a release:

1. Bump version in `pyproject.toml`.
2. Add an entry to `CHANGELOG.md`.
3. Tag with `git tag v0.x.y`.
4. Push: `git push origin main --follow-tags`.

---

## Release Checklist

```bash
pytest --cov=a2ui --cov-report=term-missing    # full coverage
python -m build --sdist --wheel              # build packages
twine check dist/*                            # sanity check metadata
twine upload dist/*                          # publish
git tag v$(.venv/bin/python -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])")
git push origin main --follow-tags
```

(Adjust `twine upload` to use your project's token / repo — see `~/.pypirc`.)

---

## Code of Conduct

Be kind. Disagree about ideas, not people. Reviewers disagree with code; they don't disparage the author. Assume good intent on confusing PRs and ask before assuming negligence.

---

## Related Docs

- [Architecture](ARCHITECTURE.md) — the layer model and why pieces are where they are
- [API reference](API.md) — every public symbol
- [Examples](EXAMPLES.md) — three runnable demos
