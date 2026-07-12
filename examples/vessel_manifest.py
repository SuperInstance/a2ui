"""
Example: Fishing vessel database with A2UI.

Demonstrates a realistic use case — a fishing fleet manager that
generates interfaces on the fly from natural language queries.
"""

from a2ui import AdaptiveInterface


# ─── Schema ───

FLEET_SCHEMA = {
    "vessels": {
        "fields": {
            "name": {"type": "string", "label": "Vessel Name"},
            "registration": {"type": "string", "label": "Reg #"},
            "length": {"type": "number", "unit": "ft"},
            "tonnage": {"type": "number", "unit": "tons"},
            "engine_hours": {"type": "number", "label": "Engine Hours"},
            "status": {
                "type": "enum",
                "options": ["active", "docked", "maintenance", "decommissioned"],
            },
            "home_port": {"type": "string", "label": "Home Port"},
            "catch_capacity": {"type": "number", "unit": "lbs"},
            "year_built": {"type": "number", "label": "Year Built"},
        },
        "primary_key": "name",
    },
    "crew": {
        "fields": {
            "name": {"type": "string", "label": "Crew Member"},
            "vessel": {"type": "relation", "relation_to": "vessels"},
            "role": {
                "type": "enum",
                "options": ["captain", "mate", "engineer", "deckhand", "cook"],
            },
            "license_number": {"type": "string", "label": "License #"},
            "years_experience": {"type": "number"},
        },
        "primary_key": "name",
    },
}


# ─── Data ───

FLEET_DATA = {
    "vessels": [
        {"name": "Ocean Rover", "registration": "NV-4471", "length": 45, "tonnage": 38,
         "engine_hours": 6200, "status": "active", "home_port": "Newport",
         "catch_capacity": 15000, "year_built": 2015},
        {"name": "Sea Sprite", "registration": "BS-2231", "length": 32, "tonnage": 18,
         "engine_hours": 3200, "status": "docked", "home_port": "Boston",
         "catch_capacity": 8000, "year_built": 2018},
        {"name": "Wave Dancer", "registration": "GL-8890", "length": 55, "tonnage": 52,
         "engine_hours": 8100, "status": "maintenance", "home_port": "Gloucester",
         "catch_capacity": 22000, "year_built": 2010},
        {"name": "Morning Star", "registration": "PT-1102", "length": 28, "tonnage": 12,
         "engine_hours": 1500, "status": "active", "home_port": "Portland",
         "catch_capacity": 5000, "year_built": 2021},
        {"name": "Storm Runner", "registration": "NV-3308", "length": 60, "tonnage": 65,
         "engine_hours": 7500, "status": "active", "home_port": "Newport",
         "catch_capacity": 28000, "year_built": 2012},
        {"name": "Lady Catherine", "registration": "BS-5544", "length": 42, "tonnage": 30,
         "engine_hours": 4800, "status": "docked", "home_port": "Boston",
         "catch_capacity": 12000, "year_built": 2016},
        {"name": "Iron Tide", "registration": "GL-6677", "length": 50, "tonnage": 45,
         "engine_hours": 9200, "status": "maintenance", "home_port": "Gloucester",
         "catch_capacity": 18000, "year_built": 2008},
    ],
    "crew": [
        {"name": "Capt. James Holt", "vessel": "Ocean Rover", "role": "captain",
         "license_number": "USCG-12345", "years_experience": 22},
        {"name": "Maria Sanchez", "vessel": "Ocean Rover", "role": "mate",
         "license_number": "USCG-22341", "years_experience": 8},
        {"name": "Capt. Sarah Chen", "vessel": "Storm Runner", "role": "captain",
         "license_number": "USCG-99887", "years_experience": 15},
        {"name": "Tom Bridges", "vessel": "Sea Sprite", "role": "captain",
         "license_number": "USCG-44221", "years_experience": 5},
        {"name": "Lisa Park", "vessel": "Wave Dancer", "role": "engineer",
         "license_number": "USCG-66112", "years_experience": 12},
    ],
}


def main():
    """Run example queries."""

    ai = AdaptiveInterface(FLEET_SCHEMA, FLEET_DATA)

    queries = [
        "show me all vessels with engine hours over 5000",
        "list active vessels sorted by length descending",
        "which vessels are in maintenance?",
        "show vessels from Newport",
        "summary of all vessels",
        "show all crew sorted by years experience descending",
    ]

    print("=" * 70)
    print("A2UI — Adaptive Interface Example: Fishing Fleet")
    print("The Whistle Layer of Working Animal Architecture")
    print("=" * 70)

    for query in queries:
        print(f"\n{'─' * 70}")
        print(f"QUERY: {query}")
        print(f"{'─' * 70}")

        spec = ai.ask(query)
        print(f"PARSED: {spec.intent}")
        print(f"VIEW: {spec.view_type} | ROWS: {len(spec.data)}")
        print()

        # Show markdown output (terminal-friendly)
        print(spec.render("markdown"))

    print(f"\n{'=' * 70}")
    print("Try your own queries with the AdaptiveInterface!")
    print("=" * 70)


if __name__ == "__main__":
    main()
