from __future__ import annotations

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


def render_python_catalog(raw_prices: dict[str, object]) -> str:
    lines: list[str] = [
        "from __future__ import annotations",
        "",
        "from enum import StrEnum",
        "from typing import Final",
        "",
        "from pydantic import BaseModel, ConfigDict",
        "",
        "",
        "class GeneratedModelPricing(BaseModel):",
        '    model_config = ConfigDict(extra="allow")',
        "",
        "    litellm_provider: str | None = None",
        "    mode: str | None = None",
        "",
        "    input_cost_per_token: float | None = None",
        "    output_cost_per_token: float | None = None",
        "    output_cost_per_reasoning_token: float | None = None",
        "    cache_read_input_token_cost: float | None = None",
        "",
        "    input_cost_per_audio_token: float | None = None",
        "    output_cost_per_image: float | None = None",
        "    file_search_cost_per_1k_calls: float | None = None",
        "    file_search_cost_per_gb_per_day: float | None = None",
        "    vector_store_cost_per_gb_per_day: float | None = None",
        "    code_interpreter_cost_per_session: float | None = None",
        "",
        "    max_input_tokens: int | str | None = None",
        "    max_output_tokens: int | str | None = None",
        "    max_tokens: int | str | None = None",
        "",
        "    deprecation_date: str | None = None",
        "",
        "    supported_endpoints: list[str] | None = None",
        "    supported_modalities: list[str] | None = None",
        "    supported_output_modalities: list[str] | None = None",
        "",
        "    supports_function_calling: bool | None = None",
        "    supports_native_streaming: bool | None = None",
        "    supports_parallel_function_calling: bool | None = None",
        "    supports_pdf_input: bool | None = None",
        "    supports_prompt_caching: bool | None = None",
        "    supports_reasoning: bool | None = None",
        "    supports_response_schema: bool | None = None",
        "    supports_system_messages: bool | None = None",
        "    supports_tool_choice: bool | None = None",
        "    supports_vision: bool | None = None",
        "",
        f"MODEL_PRICES_RAW: dict[str, object] = {pformat(raw_prices, sort_dicts=True, width=120)}",
        "",
        "",
        "class ModelName(StrEnum):",
    ]

    model_keys = sorted(k for k in raw_prices.keys() if k != "sample_spec")
    members: list[tuple[str, str, str]] = []

    if not model_keys:
        lines.append("    pass")
    else:
        used_names: set[str] = set()
        for model_name in model_keys:
            enum_name = _enum_name_for_model(model_name, used_names)
            lines.append(f"    {enum_name} = {model_name!r}")
            members.append((model_name, enum_name, _pricing_var_name(enum_name)))

    lines.extend(
        [
            "",
            "SAMPLE_SPEC: Final[GeneratedModelPricing | None] = (",
            '    GeneratedModelPricing.model_validate(MODEL_PRICES_RAW["sample_spec"])',
            '    if isinstance(MODEL_PRICES_RAW.get("sample_spec"), dict)',
            "    else None",
            ")",
            "",
            "MODEL_NAMES: tuple[str, ...] = tuple(model.value for model in ModelName)",
            "",
        ]
    )

    for model_name, _enum_name, pricing_var in members:
        lines.append(
            f"{pricing_var}: Final[GeneratedModelPricing] = GeneratedModelPricing.model_validate(MODEL_PRICES_RAW[{model_name!r}])"
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
