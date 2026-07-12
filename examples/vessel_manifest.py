"""Example: Fishing Vessel Database with A2UI.

Demonstrates a full schema with entities, relationships, and
several intent-driven interface renders.
"""

from a2ui import AdaptiveInterface, Schema, Entity, Field


def build_schema() -> Schema:
    """Build the vessel manifest schema."""
    return Schema(
        entities=[
            Entity(
                name="vessel",
                label="Vessel",
                fields=[
                    Field(name="name", type="text", label="Vessel Name", required=True),
                    Field(name="registration", type="text", label="Registration #"),
                    Field(name="length", type="number", label="Length", unit="ft"),
                    Field(name="tonnage", type="number", label="Tonnage", unit="t"),
                    Field(name="home_port", type="text", label="Home Port"),
                    Field(
                        name="status",
                        type="enum",
                        label="Status",
                        options=["active", "docked", "maintenance", "decommissioned"],
                        default="docked",
                    ),
                    Field(name="acquired", type="date", label="Date Acquired"),
                    Field(name="crew_count", type="number", label="Crew Size"),
                ],
            ),
            Entity(
                name="catch",
                label="Catch Log",
                fields=[
                    Field(name="species", type="text", label="Species", required=True),
                    Field(name="weight", type="number", label="Weight", unit="kg"),
                    Field(name="vessel_id", type="reference", label="Vessel", reference="vessel"),
                    Field(
                        name="method",
                        type="enum",
                        label="Fishing Method",
                        options=["trawl", "longline", "pot", "gillnet", "handline"],
                    ),
                    Field(name="date", type="date", label="Catch Date"),
                    Field(name="location", type="text", label="Coordinates"),
                ],
            ),
            Entity(
                name="crew",
                label="Crew Member",
                fields=[
                    Field(name="name", type="text", label="Full Name", required=True),
                    Field(name="role", type="text", label="Role"),
                    Field(
                        name="license_type",
                        type="enum",
                        label="License",
                        options=["master", "mate", "engineer", "deckhand", "cook"],
                    ),
                    Field(name="vessel_id", type="reference", label="Assigned Vessel", reference="vessel"),
                    Field(name="hire_date", type="date", label="Hire Date"),
                ],
            ),
        ],
    )


def main():
    schema = build_schema()
    ai = AdaptiveInterface(schema)

    print("=" * 60)
    print("A2UI — Vessel Manifest Demo")
    print("The Whistle Layer")
    print("=" * 60)

    # --- List View ---
    print("\n## Intent: 'show all active vessels sorted by length desc'\n")
    print(ai.to_markdown("show all active vessels sorted by length desc"))

    # --- Form View ---
    print("\n## Intent: 'new vessel'\n")
    print(ai.to_markdown("new vessel"))

    # --- JSON Output ---
    print("\n## Intent: 'new catch' (JSON)\n")
    print(ai.to_json("new catch"))

    # --- HTML Output ---
    print("\n## Intent: 'show crew' (HTML preview)\n")
    html = ai.to_html("show crew")
    # Just show first 500 chars
    print(html[:500] + "\n... [truncated]")

    # --- Chart View ---
    print("\n## Intent: 'chart vessels' (JSON)\n")
    print(ai.to_json("chart vessels"))


if __name__ == "__main__":
    main()
