# A2UI API Reference

Complete public API for **version 0.1.x** of A2UI. Every symbol exported from `a2ui` is documented here with signatures, attributes, and usage.

---

## Top-level Imports

```python
from a2ui import (
    AdaptiveInterface,   # main entry point
    Schema, Entity, Field, FieldType, ViewType,
    Intent, parse_intent,
    InterfaceSpec, InterfaceComponent,
    HTMLRenderer, MarkdownRenderer, JSONRenderer,
)
```

`Filter` and `Sort` live in `a2ui.intent`:

```python
from a2ui.intent import Filter, Sort
```

---

## 1. AdaptiveInterface

```python
class AdaptiveInterface(schema: Schema)
```

The main entry point. Pass a schema once, then call `render()`, `to_html()`, `to_markdown()`, or `to_json()` with natural-language intents.

### Constructor

```python
AdaptiveInterface(schema: Schema) -> None
```

| Argument | Type | Description |
|----------|------|-------------|
| `schema` | `Schema` | The data schema describing entities and fields. Required. |

**Example:**
```python
ai = AdaptiveInterface(my_schema)
```

### `render(intent_str)`

```python
def render(intent_str: str) -> InterfaceSpec
```

Parse a natural-language intent string and return an `InterfaceSpec`.

| Argument | Type | Description |
|----------|------|-------------|
| `intent_str` | `str` | Natural-language input. E.g. `"show all vessels over 50ft sorted by length desc"`. |

**Returns:** `InterfaceSpec`

**Raises:** Nothing currently — unknown entities gracefully fall back to a navigation list.

```python
spec = ai.render("show all vessels over 50ft")
```

### `render_intent(intent)`

```python
def render_intent(intent: Intent) -> InterfaceSpec
```

Build an `InterfaceSpec` from an already-parsed `Intent`. Use this when you have a custom intent source (a JWT claim, a domain-specific parser, an LLM).

```python
from a2ui.intent import Intent, Filter, Sort

intent = Intent(
    action="list",
    entity="vessel",
    filters=[Filter(field="length", operator="gt", value=50.0)],
    sort=Sort(field="length", direction="desc"),
    raw="custom",
)
spec = ai.render_intent(intent)
```

### `to_html(intent_str)`, `to_markdown(intent_str)`, `to_json(intent_str)`

```python
def to_html(intent_str: str) -> str
def to_markdown(intent_str: str) -> str
def to_json(intent_str: str) -> str
```

Convenience wrappers around `render()` + the matching renderer. They do exactly:

```python
def to_html(self, intent_str):
    return self.render(intent_str).to_html()
```

| Method | Output format | Renderer used |
|--------|---------------|---------------|
| `to_html` | Self-contained HTML doc | `HTMLRenderer` (inline LCARS CSS) |
| `to_markdown` | GitHub-flavored Markdown | `MarkdownRenderer` (tables, bold) |
| `to_json` | JSON string (`indent=2`) | `JSONRenderer` |

---

## 2. Schema

```python
@dataclass
class Schema:
    entities: list[Entity] = []
```

Top-level data description. Every other object references back to it.

### `Schema(entities=[...])`

```python
Schema(
    entities=[
        Entity(name="vessel", fields=[...]),
        Entity(name="catch", fields=[...]),
    ],
)
```

### `Schema.get_entity(name) -> Entity | None`

Look up an entity by name, label, or plural. Case-insensitive.

```python
schema.get_entity("vessel")    # by name
schema.get_entity("Vessel")    # case-insensitive
schema.get_entity("Vessels")   # plural tolerant
schema.get_entity("Fishing Vessel") # by label, if set
```

### `Schema.entity_names() -> list[str]`

Machine names of all entities, in declaration order.

```python
schema.entity_names()  # ['vessel', 'catch']
```

### `Schema.to_dict() -> dict`

Serializes to a plain dictionary (used by JSON output, debugging).

---

## 3. Entity

```python
@dataclass
class Entity(
    name: str,
    label: str | None = None,
    fields: list[Field] = [],
    primary_key: str | None = None,
)
```

One logical data entity (a "table" in admin framework terms).

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str` | required | Machine name. Used in intent matching and command strings. |
| `label` | `str` or `None` | `None` (auto) | Display label. Defaults to `name.replace("_", " ").title()`. |
| `fields` | `list[Field]` | `[]` | Ordered list of fields. First field becomes the implicit `primary_key`. |
| `primary_key` | `str` or `None` | `None` | Override the primary key. |

### `Entity.get_field(name) -> Field | None`

```python
entity.get_field("length")
entity.get_field("name_that_does_not_exist")  # None
```

### `Entity.to_dict() -> dict`

Serialize to a `dict`. Includes `name`, `label`, `primary_key`, and `fields` (each as their dict form).

---

## 4. Field

```python
@dataclass
class Field(
    name: str,
    type: FieldType | str = FieldType.TEXT,
    label: str | None = None,
    required: bool = False,
    unit: str | None = None,
    options: list[str] | None = None,
    reference: str | None = None,
    default: Any = None,
)
```

A single field on an entity.

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str` | required | Machine name. |
| `type` | `FieldType` or `str` | `TEXT` | One of: `text`, `number`, `date`, `enum`, `reference`. String forms are coerced via `__post_init__`. |
| `label` | `str` or `None` | `None` (auto) | Display label. Defaults to title-cased name. |
| `required` | `bool` | `False` | Whether forms must have a value. Propagates to InterfaceComponent → HTML `required` attribute and Markdown "Required" column. |
| `unit` | `str` or `None` | `None` | Optional unit suffix (`"ft"`, `"kg"`). Appears in labels and metadata. |
| `options` | `list[str]` or `None` | `None` | For `enum` fields, the valid choices. |
| `reference` | `str` or `None` | `None` | For `reference` fields, the target entity name (e.g. `"vessel"`). |
| `default` | `Any` | `None` | Default value for forms. |

### Examples

```python
# A required text field
Field(name="name", type="text", required=True)

# A number with units
Field(name="length", type="number", unit="ft")

# An enum with options
Field(
    name="status",
    type="enum",
    options=["active", "docked", "maintenance"],
    default="docked",
)

# A foreign key to another entity
Field(name="vessel_id", type="reference", reference="vessel")
```

### `Field.to_dict() -> dict`

Serialize. Includes only the keys that have values (e.g. `unit` is omitted if `None`).

---

## 5. FieldType

```python
class FieldType(str, Enum):
    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    ENUM = "enum"
    REFERENCE = "reference"
```

The five supported field types.

| Value | Use for | HTML input |
|-------|---------|------------|
| `TEXT` | Strings, names, identifiers | `<input type="text">` |
| `NUMBER` | Quantities, measurements | `<input type="number">` |
| `DATE` | Dates | `<input type="date">` |
| `ENUM` | Fixed choices | `<select>` with `<option>`s |
| `REFERENCE` | Foreign keys | `text` input with `data-reference` attribute (you wire up the picker) |

`FieldType` subclasses `str`, so `Field(type="text")` and `Field(type=FieldType.TEXT)` are equivalent and both produce the `"text"` value in JSON output.

---

## 6. ViewType

```python
class ViewType(str, Enum):
    LIST = "list"
    DETAIL = "detail"
    FORM = "form"
    DASHBOARD = "dashboard"
    CHART = "chart"
```

The five shapes an interface can take. `AdaptiveInterface` picks one based on the intent's `action`:

| Action keyword(s) | `ViewType` |
|-------------------|-----------|
| `show`, `list`, `display`, `dashboard` | `LIST` |
| `view`, `see` | `DETAIL` |
| `new`, `add`, `create`, `edit`, `modify`, `update` | `FORM` |
| `delete`, `remove` | `LIST` (with delete affordance) |
| `chart`, `plot`, `graph` | `CHART` |

Unrecognized intents default to `LIST`.

---

## 7. Intent

```python
@dataclass
class Intent(
    action: str = "list",
    entity: str = "",
    filters: list[Filter] = [],
    sort: Sort | None = None,
    raw: str = "",
    view_hint: ViewType | None = None,
)
```

A fully-parsed user intent. Produced by `parse_intent()` or constructed manually.

| Attribute | Type | Description |
|-----------|------|-------------|
| `action` | `str` | One of: `list`, `create`, `edit`, `detail`, `delete`, `chart`. |
| `entity` | `str` | Resolved schema entity name. |
| `filters` | `list[Filter]` | Active filters. |
| `sort` | `Sort` or `None` | Optional sort directive. |
| `raw` | `str` | Original input string. |
| `view_hint` | `ViewType` or `None` | Suggested view type, derived from action. |

### `Intent.to_dict() -> dict`

Serialize (used in `InterfaceSpec.to_dict()`'s `intent` field).

---

## 8. `parse_intent(text, schema)`

```python
def parse_intent(text: str, schema: Schema) -> Intent
```

Parse a natural-language string into an `Intent`. **Synchronous, deterministic, no I/O.**

### Recognized action keywords (first-word or anywhere)

| Keyword(s) | Resulting action |
|------------|------------------|
| `show`, `list`, `display`, `dashboard` | `list` |
| `view`, `see` | `detail` |
| `new`, `add`, `create` | `create` |
| `edit`, `modify`, `update` | `edit` |
| `delete`, `remove` | `delete` |
| `chart`, `plot`, `graph` | `chart` |

### Recognized comparison filter syntax

| Expression | Resulting filter |
|------------|------------------|
| `<field> over <n>` | `Filter(field, gt, <n>)` |
| `<field> under <n>` | `Filter(field, lt, <n>)` |
| `<field> above / greater than <n>` | `gt` |
| `<field> below / less than <n>` | `lt` |
| `<field> at least <n>` | `gte` |
| `<field> at most <n>` | `lte` |
| `<field> is <value>` / `<field> = <value>` | `eq` |

If a comparison has no explicit field name, the parser attaches it to the **first numeric field** on the entity.

### Recognized equality filter syntax

```python
"show vessels where status is active"
"show vessels status = active"
```

Both produce `Filter(field="status", operator="eq", value="active")`.

### Recognized sort syntax

| Expression | Resulting sort |
|------------|----------------|
| `sorted by length` | `Sort(length, asc)` |
| `sorted by length desc[ending]` | `Sort(length, desc)` |
| `order by tonnage` | `Sort(tonnage, asc)` |

### Entity resolution

The parser tries the schema's entities in declaration order, matching the **machine name**, **label**, or **plural** of either, case-insensitive. If no entity matches, it falls back to the first entity in the schema.

### Examples

```python
parse_intent("show all vessels", schema)
# Intent(action='list', entity='vessel', filters=[], sort=None, view_hint=ViewType.LIST)

parse_intent("show vessels over 50", schema)
# Intent(action='list', entity='vessel',
#        filters=[Filter(field='length', operator='gt', value=50.0)],
#        view_hint=ViewType.LIST)

parse_intent("chart vessels sorted by tonnage desc", schema)
# Intent(action='chart', entity='vessel', sort=Sort('tonnage','desc'),
#        view_hint=ViewType.CHART)
```

---

## 9. Filter and Sort

### Filter

```python
@dataclass
class Filter(field: str, operator: str = "eq", value: Any = None)
```

| Field | Description |
|-------|-------------|
| `field` | Field name being filtered. |
| `operator` | One of: `eq`, `ne`, `gt`, `lt`, `gte`, `lte`. |
| `value` | The comparison value. |

### Sort

```python
@dataclass
class Sort(field: str, direction: str = "asc")
```

| Field | Description |
|-------|-------------|
| `field` | Field name. |
| `direction` | `"asc"` or `"desc"`. |

Both have `.to_dict()` returning their fields.

---

## 10. InterfaceSpec

```python
@dataclass
class InterfaceSpec(
    title: str = "",
    view_type: ViewType = ViewType.LIST,
    entity: str | None = None,
    components: list[InterfaceComponent] = [],
    filters: list = [],
    sort: Any = None,
    intent: Intent | None = None,
)
```

The intermediate representation between intent and rendering.

| Attribute | Type | Description |
|-----------|------|-------------|
| `title` | `str` | Display title. |
| `view_type` | `ViewType` | The chosen view shape. |
| `entity` | `str` or `None` | Target entity name. |
| `components` | `list[InterfaceComponent]` | The interface elements (columns, inputs, buttons…). |
| `filters` | `list[Filter]` | Echoed from intent. |
| `sort` | `Sort` or `None` | Echoed from intent. |
| `intent` | `Intent` or `None` | The original parsed intent. |

### Methods

#### `InterfaceSpec.to_dict() -> dict`

Serialize. Used internally by `JSONRenderer` and by tests.

#### `InterfaceSpec.to_json(indent=2) -> str`

JSON string via `json.dumps(self.to_dict(), indent=indent)`.

#### `InterfaceSpec.to_html() -> str`

Convenience: `HTMLRenderer().render(self)`.

#### `InterfaceSpec.to_markdown() -> str`

Convenience: `MarkdownRenderer().render(self)`.

---

## 11. InterfaceComponent

```python
@dataclass
class InterfaceComponent(
    component_type: str = "field",
    label: str = "",
    field: str | None = None,
    sortable: bool = False,
    input_type: str | None = None,
    options: list[str] | None = None,
    reference: str | None = None,
    default: Any = None,
    required: bool = False,
    action: str | None = None,
    variant: str | None = None,
    actions: list[dict] | None = None,
    fields: list[str] | None = None,
)
```

A single UI element. Type-driven: `component_type` selects which other fields matter.

| `component_type` | Key fields |
|------------------|------------|
| `column` | `label`, `field`, `sortable` |
| `field` | `label`, `field` |
| `input` | `label`, `field`, `input_type`, `options`, `reference`, `default`, `required` |
| `button` | `label`, `action`, `variant` |
| `actions` | `label`, `actions` |
| `chart_axis` | `label`, `fields` |
| `nav_item` | `label`, `action` |
| `card` | `label`, `field` |

`required` (`bool`, default `False`) is propagated from `Field.required` in form views and surfaces as the HTML `required` attribute plus a "Yes" cell in the Markdown form table.

`InterfaceComponent.to_dict()` returns a dictionary containing only the fields that have values.

---

## 12. Renderers

All renderers subclass `BaseRenderer`:

```python
class BaseRenderer:
    def render(self, spec: InterfaceSpec) -> str:
        raise NotImplementedError
```

### `HTMLRenderer`

Renders a self-contained HTML document with inline CSS, dark background, bold colors, and rounded elements (LCARS-inspired).

```python
from a2ui import HTMLRenderer
html = HTMLRenderer().render(spec)
```

- Escapes all user text (titles, field labels, options) — XSS-safe for renderer-built strings.
- Form inputs have `for`/`id` linking labels for accessibility.
- `required` form fields emit the `required` attribute.

### `MarkdownRenderer`

Renders GitHub-flavored Markdown. Tables for list views, field/type tables for forms, bold labels for details.

```python
from a2ui import MarkdownRenderer
md = MarkdownRenderer().render(spec)
```

### `JSONRenderer`

Renders pretty-printed JSON of `spec.to_dict()`.

```python
from a2ui import JSONRenderer
j = JSONRenderer().render(spec, indent=2)
```

### Writing your own renderer

```python
from a2ui.renderers import BaseRenderer
from a2ui.interface import InterfaceSpec

class TextRenderer(BaseRenderer):
    def render(self, spec: InterfaceSpec) -> str:
        # Walk spec.components and emit whatever you want.
        return "\n".join(c.label for c in spec.components)
```

---

## 13. Intent Grammar Summary

A compact grammar summary for the parser. See [`parse_intent`](#7-parse_intenttext-schema) for full semantics.

```
intent     := <action_keyword>? <entity_word>+ <filters>? <sort>?
filters    := <comp_filter> | <eq_filter>
comp_filter := <word>? ("over"|"under"|"above"|"below"|"greater than"
             |"less than"|"more than"|"at least"|"at most") <number>
eq_filter  := <word> ("is"|"="|"equals"|"==") <word>
sort       := ("sorted by"|"order by") <word> ("asc"|"desc"|"ascending"|"descending")?
```

Action keywords are also recognized **anywhere in the input** for a small allow-list (`chart`, `plot`, `graph`).

A `<word>` is matched against entity and field names by the schema-aware resolver; numbers are floats; entity matching is case-insensitive and tolerates plurals.

---

## Related Docs

- [Architecture](ARCHITECTURE.md)
- [Examples](EXAMPLES.md)
- [Contributing](CONTRIBUTING.md)
