"""
Intent parsing — turn natural language into structured Intent.

The Whistle Layer doesn't need full NLP. It needs enough to understand
what the user wants, and the schema provides the vocabulary.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

from .schema import Schema, FieldType


@dataclass
class Intent:
    """A parsed user intent — what they want to do."""

    action: str = "show"
    entity: str = ""
    fields: list[str] = field(default_factory=list)
    filters: list[dict] = field(default_factory=list)
    sort_by: Optional[tuple[str, str]] = None  # (field, "asc"|"desc")
    raw: str = ""

    def __repr__(self) -> str:
        parts = [f"action={self.action}", f"entity={self.entity}"]
        if self.fields:
            parts.append(f"fields={self.fields}")
        if self.filters:
            parts.append(f"filters={self.filters}")
        if self.sort_by:
            parts.append(f"sort={self.sort_by}")
        return f"Intent({', '.join(parts)})"


class IntentParser:
    """
    Parse natural language into structured Intents.

    Uses keyword matching + schema awareness. Not trying to be ChatGPT —
    trying to be a good whistle.

        >>> parser = IntentParser(schema)
        >>> intent = parser.parse("show vessels with hours over 5000")
        >>> intent.action
        'show'
        >>> intent.filters
        [{'field': 'engine_hours', 'op': 'gt', 'value': 5000}]
    """

    # Action keywords → canonical actions
    ACTION_MAP = {
        "show": "show",
        "list": "list",
        "find": "find",
        "search": "search",
        "which": "which",
        "get": "get",
        "view": "view",
        "detail": "detail",
        "inspect": "inspect",
        "add": "add",
        "create": "add",
        "new": "add",
        "edit": "edit",
        "update": "edit",
        "modify": "edit",
        "delete": "delete",
        "remove": "delete",
        "summary": "summary",
        "overview": "summary",
        "stats": "summary",
        "count": "summary",
    }

    # Operator patterns: (regex, operator)
    OPERATOR_PATTERNS = [
        (r"(?:greater\s+than\s+or\s+equal\s+to|at\s+least|>=|≥)\s*(\S+)", "gte"),
        (r"(?:less\s+than\s+or\s+equal\s+to|at\s+most|<=|≤)\s*(\S+)", "lte"),
        (r"(?:greater\s+than|over|above|more\s+than|>|>)\s*(\S+)", "gt"),
        (r"(?:less\s+than|under|below|fewer\s+than|<)\s*(\S+)", "lt"),
        (r"(?:equal\s+to|equals|is|=|==)\s*(\S+)", "eq"),
        (r"(?:not\s+equal\s+to|not|!=|≠)\s*(\S+)", "ne"),
        (r"(?:contains|includes?|like)\s+(\S+)", "contains"),
    ]

    # Sort patterns — capture multi-word field names
    SORT_ASC = re.compile(
        r"(?:sort(?:ed)?(?:\s+by)?|order(?:ed)?(?:\s+by)?)\s+(.+?)"
        r"(?:\s+(?:ascending|asc|a-z|smallest|oldest))?(?:\s*$|\s+(?:and|with|where)\b)",
        re.IGNORECASE,
    )
    SORT_DESC = re.compile(
        r"(?:sort(?:ed)?(?:\s+by)?|order(?:ed)?(?:\s+by)?)\s+(.+?)"
        r"\s+(?:descending|desc|z-a|largest|newest|biggest)",
        re.IGNORECASE,
    )
    SORT_NEWEST = re.compile(r"(?:newest|latest|most\s+recent)\s+(.+?)$", re.IGNORECASE)
    SORT_OLDEST = re.compile(r"(?:oldest|earliest)\s+(.+?)$", re.IGNORECASE)

    def __init__(self, schema: Schema):
        self.schema = schema

    def parse(self, text: str) -> Intent:
        """
        Parse a natural language string into an Intent.

        Args:
            text: Natural language, e.g. "show vessels with hours over 5000"

        Returns:
            A structured Intent
        """
        text_lower = text.lower().strip()
        intent = Intent(raw=text)

        # Parse action
        intent.action = self._parse_action(text_lower)

        # Parse entity
        intent.entity = self._parse_entity(text_lower)

        # Parse filters
        intent.filters = self._parse_filters(text_lower, text)

        # Parse sort
        intent.sort_by = self._parse_sort(text_lower)

        # Parse requested fields
        intent.fields = self._parse_fields(text_lower)

        return intent

    def _parse_action(self, text: str) -> str:
        """Extract the action verb."""
        words = text.split()
        for word in words:
            clean = re.sub(r"[^a-z]", "", word)
            if clean in self.ACTION_MAP:
                return self.ACTION_MAP[clean]
        return "show"

    def _parse_entity(self, text: str) -> str:
        """Extract the entity name using schema awareness."""
        # Try to find an entity name in the text
        for entity in self.schema.entities:
            entity_lower = entity.lower()
            singular = self.schema._singular(entity).lower()
            plural = self.schema._plural(entity).lower()

            if entity_lower in text or plural in text or singular in text:
                return entity

        # Fallback: try word-by-word
        words = re.findall(r"\b\w+\b", text)
        for entity in self.schema.entities:
            entity_lower = entity.lower()
            for word in words:
                if word.lower() == entity_lower:
                    return entity

        return self.schema.entities[0] if self.schema.entities else ""

    def _parse_filters(self, text_lower: str, original: str) -> list[dict]:
        """Extract filter conditions from the text."""
        filters = []

        intent_entity = self._parse_entity(text_lower)
        if not intent_entity:
            return filters

        try:
            field_map = self._build_field_lookup(intent_entity)
        except KeyError:
            return filters

        # Try each operator pattern
        for pattern, op in self.OPERATOR_PATTERNS:
            for match in re.finditer(pattern, text_lower):
                value_str = match.group(1)
                # Try to find which field this filter refers to
                # Look backwards from the match for a field name
                start = match.start()
                preceding = text_lower[:start]
                field_name = self._find_field_in_text(preceding, field_map)

                if field_name:
                    parsed_value = self._coerce_value(field_name, intent_entity, value_str)
                    filters.append({
                        "field": field_name,
                        "op": op,
                        "value": parsed_value,
                    })

        # Also check for "is <status>" patterns (enum matching)
        try:
            fields = self.schema.get_fields(intent_entity)
            for fname, spec in fields.items():
                if spec.type == FieldType.ENUM:
                    for option in spec.options:
                        if re.search(rf"\b{re.escape(option.lower())}\b", text_lower):
                            # Check we haven't already captured this
                            already = any(
                                f["field"] == fname and f["value"] == option
                                for f in filters
                            )
                            if not already:
                                filters.append({
                                    "field": fname,
                                    "op": "eq",
                                    "value": option,
                                })
        except KeyError:
            pass

        # Deduplicate
        seen = set()
        unique = []
        for f in filters:
            key = (f["field"], f["op"], str(f["value"]))
            if key not in seen:
                seen.add(key)
                unique.append(f)

        return unique

    def _parse_sort(self, text: str) -> Optional[tuple[str, str]]:
        """Extract sort specification."""
        # Try explicit descending
        m = self.SORT_DESC.search(text)
        if m:
            field_word = m.group(1)
            resolved = self._try_resolve_field(field_word)
            if resolved:
                return (resolved, "desc")

        # Try explicit ascending
        m = self.SORT_ASC.search(text)
        if m:
            field_word = m.group(1)
            resolved = self._try_resolve_field(field_word)
            if resolved:
                return (resolved, "asc")

        # Try "newest/latest <field>"
        m = self.SORT_NEWEST.search(text)
        if m:
            field_word = m.group(1)
            resolved = self._try_resolve_field(field_word)
            if resolved:
                return (resolved, "desc")

        # Try "oldest <field>"
        m = self.SORT_OLDEST.search(text)
        if m:
            field_word = m.group(1)
            resolved = self._try_resolve_field(field_word)
            if resolved:
                return (resolved, "asc")

        return None

    def _parse_fields(self, text: str) -> list[str]:
        """Extract explicitly requested fields."""
        # Look for "show only X and Y" or "display X, Y"
        patterns = [
            r"(?:show|display|list|select)\s+(?:only\s+)?([\w\s,]+?)(?:\s+(?:from|in|where|with|sorted|ordered|of)\b)",
            r"(?:fields?|columns?)\s*[:=]\s*([\w\s,]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                raw_fields = match.group(1)
                field_names = re.split(r"[,\s]+", raw_fields.strip())
                resolved = []
                for fn in field_names:
                    fn = fn.strip()
                    if fn:
                        resolved_name = self._try_resolve_field(fn)
                        if resolved_name and resolved_name not in resolved:
                            resolved.append(resolved_name)
                if resolved:
                    return resolved
        return []

    def _build_field_lookup(self, entity: str) -> dict[str, str]:
        """Build a lowercase field name → canonical name map."""
        result = {}
        fields = self.schema.get_fields(entity)
        for fname, spec in fields.items():
            result[fname.lower()] = fname
            result[spec.label.lower()] = fname
            # Also map without underscores
            result[fname.replace("_", "").lower()] = fname
        return result

    def _find_field_in_text(self, text: str, field_map: dict[str, str]) -> Optional[str]:
        """Find the last field name mentioned in the given text."""
        # Check multi-word labels first (longer = more specific)
        sorted_keys = sorted(field_map.keys(), key=len, reverse=True)
        for key in sorted_keys:
            if key in text:
                return field_map[key]
        return None

    def _try_resolve_field(self, word: str) -> Optional[str]:
        """Try to resolve a word to a field name across all entities."""
        word_lower = word.lower().strip()
        # Normalize: try with underscores, spaces, or no separator
        word_underscore = word_lower.replace(" ", "_")
        word_nospace = word_lower.replace(" ", "").replace("_", "")
        for entity in self.schema.entities:
            try:
                fields = self.schema.get_fields(entity)
                for fname, spec in fields.items():
                    fn_lower = fname.lower()
                    fn_nospace = fname.replace("_", "").lower()
                    if fn_lower == word_underscore or fn_lower == word_lower:
                        return fname
                    if spec.label.lower() == word_lower:
                        return fname
                    if fn_nospace == word_nospace:
                        return fname
            except KeyError:
                continue
        return None

    def _coerce_value(self, field_name: str, entity: str, value_str: str) -> Any:
        """Coerce a string value to the appropriate type based on schema."""
        try:
            spec = self.schema.get_field(entity, field_name)
            if spec.type in (FieldType.NUMBER,):
                # Strip non-numeric prefix/suffix
                cleaned = re.sub(r"[^\d.-]", "", value_str)
                if "." in cleaned:
                    return float(cleaned)
                return int(cleaned) if cleaned else 0
            elif spec.type == FieldType.BOOLEAN:
                return value_str.lower() in ("true", "yes", "1", "active")
            else:
                # Strip quotes if present
                cleaned = value_str.strip("\"'.,")
                return cleaned
        except (KeyError, ValueError):
            return value_str.strip("\"'.,")
