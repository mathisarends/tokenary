from __future__ import annotations

import json

import pytest

from tokenary.generator.downloader import fetch_model_prices_raw, write_raw_prices_file
from tokenary.generator.generator import render_python_catalog, write_python_catalog_file


class _FakeResponse:
    def __init__(self, payload: str) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return self._payload.encode("utf-8")

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_fetch_model_prices_raw_returns_json_object(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = json.dumps({"sample_spec": {}, "my-model": {"mode": "chat"}})

    def fake_urlopen(request, timeout=30):
        assert timeout == 30
        assert request.full_url == "https://example.test/prices.json"
        return _FakeResponse(payload)

    monkeypatch.setattr("tokenary.generator.downloader.urlopen", fake_urlopen)

    result = fetch_model_prices_raw(url="https://example.test/prices.json")

    assert result["my-model"]["mode"] == "chat"


def test_fetch_model_prices_raw_rejects_non_object(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(request, timeout=30):
        return _FakeResponse("[]")

    monkeypatch.setattr("tokenary.generator.downloader.urlopen", fake_urlopen)

    with pytest.raises(ValueError, match="not a JSON object"):
        fetch_model_prices_raw(url="https://example.test/prices.json")


def test_write_raw_prices_file_creates_missing_parent_dirs(tmp_path) -> None:
    output_file = tmp_path / "nested" / "catalog.json"

    written_path = write_raw_prices_file(
        raw_prices={"sample_spec": {}, "model-a": {"input_cost_per_token": 0.1}},
        output_path=output_file,
    )

    assert written_path == output_file
    assert output_file.exists()


def test_render_python_catalog_emits_enum_and_pricing_constructors() -> None:
    rendered = render_python_catalog(
        {
            "sample_spec": {},
            "azure/gpt-35-turbo-0125": {"mode": "chat"},
            "1024-x-1024/dall-e-2": {"mode": "image_generation"},
        }
    )

    assert "class ModelName(StrEnum):" in rendered
    assert "AZURE_GPT_35_TURBO_0125" in rendered
    assert "MODEL_1024_X_1024_DALL_E_2" in rendered
    assert "GeneratedModelPricing(" in rendered
    assert "MODEL_PRICES_RAW" not in rendered


def test_write_python_catalog_file_writes_importable_module(tmp_path) -> None:
    py_path = tmp_path / "prices.py"

    write_python_catalog_file(
        {
            "sample_spec": {},
            "azure/gpt-35-turbo-0125": {
                "mode": "chat",
                "input_cost_per_token": 0.000001,
            },
        },
        py_path,
    )

    generated = py_path.read_text(encoding="utf-8")

    assert "MODEL_PRICINGS_BY_NAME" in generated
    assert "PRICING_AZURE_GPT_35_TURBO_0125" in generated
