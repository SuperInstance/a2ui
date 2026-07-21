# A2UI Examples

Three end-to-end examples, ordered from shortest to most extensive. All run as standalone Python scripts — no extra dependencies.

| # | Example | What it shows |
|---|---------|---------------|
| 1 | [`vessel_manifest.py`](#1-fishing-vessel-manifest) | All view types (list, form, detail, chart), HTML + Markdown + JSON output |
| 2 | [`issue_tracker.py`](#2-issue-tracker) | Non-fishing domain, multi-entity relationships, filters across entities |
| 3 | [`custom_renderer.py`](#3-custom-renderer-terminal-output) | Subclass `BaseRenderer` to add a new output format (ANSI terminal) |

Run any example from the repo root:

```bash
python examples/vessel_manifest.py
python examples/issue_tracker.py
python examples/custom_renderer.py
```

---

## 1. Fishing Vessel Manifest

**File:** [`examples/vessel_manifest.py`](../examples/vessel_manifest.py)

The canonical "show off every view type" example. Builds a three-entity fishing domain (vessel, catch log, crew member) and renders the same intent through three output formats.

### Schema

```python
schema = Schema(
    entities=[
        Entity(name="vessel", label="Vessel", fields=[
            Field(name="name", type="text", required=True),
            Field(name="registration", type="text"),
            Field(name="length", type="number", unit="ft"),
            Field(name="tonnage", type="number", unit="t"),
            Field(name="home_port", type="text"),
            Field(name="status", type="enum",
                  options=["active", "docked", "maintenance", "decommissioned"],
                  default="docked"),
            Field(name="acquired", type="date"),
            Field(name="crew_count", type="number", label="Crew Size"),
        ]),
        Entity(name="catch", label="Catch Log", fields=[
            Field(name="species", type="text", required=True),
            Field(name="weight", type="number", unit="kg"),
            Field(name="vessel_id", type="reference", reference="vessel"),
            Field(name="method", type="enum",
                  options=["trawl", "longline", "pot", "gillnet", "handline"]),
            Field(name="date", type="date"),
            Field(name="location", type="text"),
        ]),
        Entity(name="crew", label="Crew Member", fields=[
            Field(name="name", type="text", required=True),
            Field(name="role", type="text"),
            Field(name="license_type", type="enum",
                  options=["master", "mate", "engineer", "deckhand", "cook"]),
            Field(name="vessel_id", type="reference", reference="vessel"),
            Field(name="hire_date", type="date"),
        ]),
    ],
)
```

### Intents exercised

```python
ai = AdaptiveInterface(schema)

ai.to_markdown("show all active vessels sorted by length desc")  # LIST
ai.to_markdown("new vessel")                                       # FORM
ai.to_json("new catch")                                           # JSON FORM
ai.to_html("show crew")                                           # HTML LIST
ai.to_json("chart vessels")                                       # CHART
```

### Expected output (abbreviated)

List view:

```
# Vessels

**Sort:** length (desc)

| Vessel Name | Registration # | Length | Tonnage | … | Actions |
| --- | --- | --- | --- | --- | --- |
| — | — | — | — | … | View Edit |
```

Form view:

```
# New Vessel

| Field | Type | Required |
| --- | --- | --- |
| Vessel Name | text | Yes |
| Length | number |  |
| Status | select (active, docked, maintenance, decommissioned) |  |
…
**[Submit]**
```

### What you'll learn

- Defining an entity with mixed field types (`text`, `number`, `enum`, `date`, `reference`)
- All three view types (LIST, FORM, CHART) from natural-language intents
- Required field propagation (now correctly reflected in Markdown + HTML)

---

## 2. Issue Tracker

**File:** [`examples/issue_tracker.py`](../examples/issue_tracker.py)

Same shape, different domain. Demonstrates that A2UI works on whatever data you describe — not just marine. It also exercises cross-entity filters and sort hints.

### Schema

```python
schema = Schema(
    entities=[
        Entity(name="project", label="Project", fields=[
            Field(name="name", type="text", required=True),
            Field(name="visibility", type="enum",
                  options=["public", "private", "internal"], default="internal"),
            Field(name="created_at", type="date"),
            Field(name="owner", type="text"),
        ]),
        Entity(name="issue", label="Issue", fields=[
            Field(name="title", type="text", required=True),
            Field(name="status", type="enum",
                  options=["open", "in_progress", "review", "closed", "wont_fix"],
                  default="open"),
            Field(name="priority", type="enum", options=["p0", "p1", "p2", "p3"]),
            Field(name="created_at", type="date"),
            Field(name="closed_at", type="date"),
            Field(name="estimate_hours", type="number", unit="h"),
            Field(name="project_id", type="reference", reference="project"),
            Field(name="assignee", type="text"),
        ]),
        Entity(name="comment", label="Comment", fields=[
            Field(name="body", type="text", required=True),
            Field(name="author", type="text"),
            Field(name="posted_at", type="date"),
            Field(name="issue_id", type="reference", reference="issue"),
        ]),
    ],
)
```

### Intents exercised

```python
ai.to_markdown("show open issues over 4 hours sorted by priority")
ai.to_markdown("new issue")
ai.to_markdown("view project")
ai.to_json("show issues where status is review")
```

### Expected output (abbreviated)

List view with filters:

```
# Issues

**Filters:**
- `estimate_hours` gt `4.0`

**Sort:** priority (asc)

| Title | Status | Priority | … | Actions |
| --- | --- | --- | --- | --- |
| — | — | — | … | View Edit |
```

### What you'll learn

- A2UI works on any domain — the engine is schema-driven
- The parser recognises multiple filter/sort patterns together
- Reference fields across entities (`issue.project_id` → `project`)

---

## 3. Custom Renderer (Terminal Output)

**File:** [`examples/custom_renderer.py`](../examples/custom_renderer.py)

Demonstrates that the rendering layer is fully pluggable. This example implements a `TerminalRenderer` that emits ANSI-coloured text — useful for CLI tools, REPLs, log lines, or anywhere HTML/Markdown aren't appropriate.

### The renderer

```python
from a2ui.renderers import BaseRenderer
from a2ui.interface import InterfaceSpec
from a2ui.schema import ViewType

class TerminalRenderer(BaseRenderer):
    BOLD = "\033[1m"
    CYAN = "\033[36m"
    # … full ANSI palette

    def render(self, spec: InterfaceSpec) -> str:
        lines = [f"{self.BOLD}{self.CYAN}== {spec.title} =={self.RESET}"]
        # … walks spec.components
```

You can extend this further:

- **JSON-Lines renderer** for streaming APIs.
- **JSX renderer** that produces React components.
- **PDF/LaTeX renderer** for printable reports.
- **Server-rendered partial** for HTMX, LiveView, htmx-style tools.

The contract is just: given a fully-built `InterfaceSpec`, produce a string.

### Intents exercised

```python
renderer = TerminalRenderer()
print(renderer.render(ai.render("show active vessels over 50 sorted by length desc")))
print(renderer.render(ai.render("new vessel")))
print(renderer.render(ai.render("view vessel")))
```

### Expected output

```
== Vessels ==
view_type: list
entity: vessel
filters: length gt 50.0
sort: length desc

Vessel Name | Length | Status | Actions
------------+--------+--------+--------
——————————— | —————— | —————— | ———————
```

### What you'll learn

- How to subclass `BaseRenderer`
- How to walk `spec.components` and switch on `spec.view_type`
- That A2UI's three-layer architecture (intent → spec → render) means you can swap any layer independently

---

## Building Your Own

A useful template:

1. **Define your schema.** Start with the entities, list their fields, mark `required=True` on whatever you can't have empty.
2. **Pick a renderer.** HTML for a web app, JSON for an API, Markdown for terminal/docs, or write your own.
3. **Choose your parser default.** Either use the built-in `parse_intent`, or write a domain-specific parser and pass an `Intent` directly to `ai.render_intent(intent)`.

```python
# Sketch
my_schema = Schema(entities=[Entity(name="...", fields=[...]), ...])
ai = AdaptiveInterface(my_schema)

# In your web framework
def index(request):
    intent = request.GET.get("intent", "show tickets")
    return HttpResponse(ai.to_html(intent))
```

For more depth on the architectural choices, see [ARCHITECTURE.md](ARCHITECTURE.md). For every public symbol, see [API.md](API.md).
