from __future__ import annotations

import keyword
from pathlib import Path
from pprint import pformat
import re

from .downloader import DEFAULT_PRICE_URL, fetch_model_prices_raw, write_raw_prices_file

DEFAULT_JSON_CATALOG_FILE = "data/model_prices.generated.json"
DEFAULT_PYTHON_CATALOG_FILE = "tokenary/_generated.py"


def get_json_catalog_path(catalog_path: str | Path | None = None) -> Path:
    return (
        Path(catalog_path)
        if catalog_path is not None
        else Path(DEFAULT_JSON_CATALOG_FILE)
    )


def get_python_catalog_path(catalog_path: str | Path | None = None) -> Path:
    return (
        Path(catalog_path)
        if catalog_path is not None
        else Path(DEFAULT_PYTHON_CATALOG_FILE)
    )


def _enum_name_for_model(model_name: str, used_names: set[str]) -> str:
    name = re.sub(r"[^0-9A-Za-z]+", "_", model_name).strip("_").upper()
    if not name:
        name = "MODEL"
    if name[0].isdigit():
        name = f"MODEL_{name}"

    base = name
    idx = 2
    while name in used_names:
        name = f"{base}_{idx}"
        idx += 1

    used_names.add(name)
    return name


def _pricing_var_name(enum_name: str) -> str:
    return f"PRICING_{enum_name}"


def _render_python_value(value: object, indent: int = 0) -> str:
    rendered = pformat(value, sort_dicts=True, width=100)
    if indent > 0 and "\n" in rendered:
        rendered = rendered.replace("\n", f"\n{' ' * indent}")
    return rendered


def _is_valid_kwarg_name(name: str) -> bool:
    return name.isidentifier() and not keyword.iskeyword(name)


def _append_pricing_constructor(
    lines: list[str],
    var_name: str,
    model_data: dict[str, object],
    annotation: str = "GeneratedModelPricing",
) -> None:
    lines.append(f"{var_name}: Final[{annotation}] = GeneratedModelPricing(")

    regular_kwargs: list[tuple[str, object]] = []
    extra_kwargs: dict[str, object] = {}

    for key in sorted(model_data.keys()):
        value = model_data[key]
        if _is_valid_kwarg_name(key):
            regular_kwargs.append((key, value))
        else:
            extra_kwargs[key] = value

    for key, value in regular_kwargs:
        lines.append(f"    {key}={_render_python_value(value, indent=8)},")

    if extra_kwargs:
        lines.append(f"    **{_render_python_value(extra_kwargs, indent=8)},")

    lines.append(")")


def render_python_catalog(raw_prices: dict[str, object]) -> str:
    lines: list[str] = [
        "from enum import StrEnum",
        "from typing import Final",
        "",
        "from tokenary.generator.schemas import GeneratedModelPricing",
        "",
        "",
        "class ModelName(StrEnum):",
    ]

    model_keys = sorted(
        k for k, v in raw_prices.items() if k != "sample_spec" and isinstance(v, dict)
    )
    members: list[tuple[str, str, str]] = []

    if not model_keys:
        lines.append("    pass")
    else:
        used_names: set[str] = set()
        for model_name in model_keys:
            enum_name = _enum_name_for_model(model_name, used_names)
            lines.append(f"    {enum_name} = {model_name!r}")
            members.append((model_name, enum_name, _pricing_var_name(enum_name)))

    lines.append("")

    sample_spec = raw_prices.get("sample_spec")
    if isinstance(sample_spec, dict):
        _append_pricing_constructor(
            lines=lines,
            var_name="SAMPLE_SPEC",
            model_data=sample_spec,
            annotation="GeneratedModelPricing | None",
        )
    else:
        lines.append("SAMPLE_SPEC: Final[GeneratedModelPricing | None] = None")

    lines.extend(
        [
            "",
            "MODEL_NAMES: tuple[str, ...] = tuple(model.value for model in ModelName)",
            "",
        ]
    )

    for model_name, _enum_name, pricing_var in members:
        model_data = raw_prices[model_name]
        if isinstance(model_data, dict):
            _append_pricing_constructor(
                lines=lines,
                var_name=pricing_var,
                model_data=model_data,
            )

    if members:
        lines.extend(["", "MODEL_PRICINGS: dict[ModelName, GeneratedModelPricing] = {"])
        for _model_name, enum_name, pricing_var in members:
            lines.append(f"    ModelName.{enum_name}: {pricing_var},")
        lines.append("}")
    else:
        lines.append("MODEL_PRICINGS: dict[ModelName, GeneratedModelPricing] = {}")

    lines.extend(
        [
            "",
            "MODEL_PRICINGS_BY_NAME: dict[str, GeneratedModelPricing] = {",
            "    model_name.value: pricing for model_name, pricing in MODEL_PRICINGS.items()",
            "}",
        ]
    )

    return "\n".join(lines) + "\n"


def write_python_catalog_file(
    raw_prices: dict[str, object], output_path: str | Path
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_python_catalog(raw_prices), encoding="utf-8")
    return path


def generate_catalog_artifacts(
    output_json_path: str | Path | None = None,
    output_python_path: str | Path | None = None,
    source_url: str = DEFAULT_PRICE_URL,
    generate_json: bool = True,
) -> tuple[Path | None, Path]:
    raw_prices = fetch_model_prices_raw(url=source_url)

    json_path: Path | None = None
    if generate_json:
        json_path = write_raw_prices_file(
            raw_prices=raw_prices, output_path=get_json_catalog_path(output_json_path)
        )

    python_path = write_python_catalog_file(
        raw_prices=raw_prices,
        output_path=get_python_catalog_path(output_python_path),
    )

    return json_path, python_path
