"""Model identifiers that retain their names across filtered catalog updates."""

import hashlib
import keyword
import re
from collections.abc import Iterable, Mapping


def make_enum_names(
    models: Iterable[str], previous_names: Mapping[str, str] | None = None
) -> dict[str, str]:
    previous = dict(previous_names or {})
    if any(
        not isinstance(alias, str)
        or not alias.isidentifier()
        or keyword.iskeyword(alias)
        or alias.startswith("_")
        for alias in previous.values()
    ):
        raise ValueError("Existing enum names must be valid public Python identifiers")
    used = {alias: model for model, alias in previous.items()}
    if len(used) != len(previous):
        raise ValueError("Existing model enum names must be unique")

    result: dict[str, str] = {}
    for model in sorted(models):
        if model in previous:
            result[model] = previous[model]
            continue
        base = re.sub(r"[^0-9A-Za-z]+", "_", model).strip("_").upper() or "MODEL"
        if base[0].isdigit():
            base = f"MODEL_{base}"
        alias = base
        if alias in used:
            digest = hashlib.sha256(model.encode("utf-8")).hexdigest().upper()
            length = 8
            alias = f"{base}_{digest[:length]}"
            while alias in used:
                length += 1
                alias = f"{base}_{digest[:length]}"
        used[alias] = model
        result[model] = alias
    return result
