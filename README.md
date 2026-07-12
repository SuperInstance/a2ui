# A2UI — Adaptive Interface

## The Whistle Layer

From **Working Animal Architecture**: the user states intent, the system reads the data schema, generates the interface.

A2UI is an LCARS-inspired adaptive interface system. You don't design UI — you describe your data, say what you want to do with it, and the interface generates itself.

### How It Works

1. **Define a schema** — describe your data entities, fields, and relationships
2. **Express intent** — "show me all vessels over 50ft" or "new entry for catch log"
3. **Get an interface** — A2UI generates an `InterfaceSpec` and renders it to HTML, Markdown, or JSON

### Quick Start

```python
from a2ui import AdaptiveInterface, Schema, Entity, Field
from a2ui.intent import parse_intent

schema = Schema(
    entities=[
        Entity(
            name="vessel",
            fields=[
                Field(name="name", type="text", label="Vessel Name"),
                Field(name="length", type="number", unit="ft"),
                Field(name="home_port", type="text"),
                Field(name="status", type="enum", options=["active", "docked", "maintenance"]),
            ],
        ),
    ],
)

ai = AdaptiveInterface(schema)
spec = ai.render("show all active vessels sorted by length")
print(spec.to_html())
```

### The Whistle

The name comes from working animals — a shepherd's whistle, a falconer's cue. You don't micromanage the dog; you give a cue and the dog figures out the terrain. A2UI does the same for interfaces: you whistle your intent, it figures out the buttons, fields, and layout.

### License

MIT
