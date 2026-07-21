"""Example: Issue Tracker with A2UI.

Demonstrates a non-fishing domain (issue tracking) and shows how a richer
schema produces useful filters and sorts from natural-language intents.
"""

from a2ui import AdaptiveInterface, Schema, Entity, Field


def build_schema() -> Schema:
    """Build an issue tracker schema with relationships and enums."""
    return Schema(
        entities=[
            Entity(
                name="project",
                label="Project",
                fields=[
                    Field(name="name", type="text", label="Project Name", required=True),
                    Field(
                        name="visibility",
                        type="enum",
                        label="Visibility",
                        options=["public", "private", "internal"],
                        default="internal",
                    ),
                    Field(name="created_at", type="date", label="Created"),
                    Field(name="owner", type="text", label="Owner"),
                ],
            ),
            Entity(
                name="issue",
                label="Issue",
                fields=[
                    Field(name="title", type="text", label="Title", required=True),
                    Field(
                        name="status",
                        type="enum",
                        label="Status",
                        options=["open", "in_progress", "review", "closed", "wont_fix"],
                        default="open",
                    ),
                    Field(
                        name="priority",
                        type="enum",
                        label="Priority",
                        options=["p0", "p1", "p2", "p3"],
                    ),
                    Field(name="created_at", type="date", label="Opened"),
                    Field(name="closed_at", type="date", label="Closed"),
                    Field(name="estimate_hours", type="number", label="Estimate (h)", unit="h"),
                    Field(name="project_id", type="reference", label="Project", reference="project"),
                    Field(name="assignee", type="text", label="Assignee"),
                ],
            ),
            Entity(
                name="comment",
                label="Comment",
                fields=[
                    Field(name="body", type="text", label="Body", required=True),
                    Field(name="author", type="text", label="Author"),
                    Field(name="posted_at", type="date", label="Posted"),
                    Field(name="issue_id", type="reference", label="Issue", reference="issue"),
                ],
            ),
        ],
    )


def main():
    schema = build_schema()
    ai = AdaptiveInterface(schema)

    print("=" * 60)
    print("A2UI — Issue Tracker Demo")
    print("=" * 60)

    # Show a specific intent: filter status, sort, project ref
    print("\n## Intent: 'show open issues over 4 hours sorted by priority'\n")
    print(ai.to_markdown("show open issues over 4 hours sorted by priority"))

    # Form for new issue, including the project reference field
    print("\n## Intent: 'new issue'\n")
    print(ai.to_markdown("new issue"))

    # Switch to a different entity with a different intent type
    print("\n## Intent: 'view project'\n")
    print(ai.to_markdown("view project"))

    # JSON output for an API consumer
    print("\n## Intent: 'show issues where status is review' (JSON)\n")
    print(ai.to_json("show issues where status is review"))


if __name__ == "__main__":
    main()
