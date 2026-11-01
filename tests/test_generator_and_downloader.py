from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import httpx2
import pytest
from pydantic import ValidationError

from tokenary import calculate
from tokenary.generator.downloader import (
    fetch_model_prices_raw,
    write_raw_prices_file,
)
from tokenary.generator.generator import (
    render_python_catalog,
    write_python_catalog_file,
)


def test_fetch_model_prices_raw_returns_typed_json_object() -> None:
    async def run():
        def handle(request):
            assert request.url == "https://example.test/prices.json"
            assert request.extensions["timeout"]["read"] == 30
            return httpx2.Response(200, json={"my-model": {"mode": "chat"}})

        async with httpx2.AsyncClient(transport=httpx2.MockTransport(handle)) as client:
            result = await fetch_model_prices_raw(
                url="https://example.test/prices.json", client=client
            )
            assert result == {"my-model": {"mode": "chat"}}

    asyncio.run(run())


@pytest.mark.parametrize("content", [b"[]", b"invalid json"])
def test_fetch_model_prices_raw_rejects_bad_payload(content) -> None:
    async def run():
        async with httpx2.AsyncClient(
            transport=httpx2.MockTransport(
                lambda r: httpx2.Response(200, content=content)
            )
        ) as client:
            with pytest.raises(ValidationError):
                await fetch_model_prices_raw(client=client)

    asyncio.run(run())


def test_fetch_model_prices_raw_checks_http_status() -> None:
    async def run():
        async with httpx2.AsyncClient(
            transport=httpx2.MockTransport(lambda r: httpx2.Response(503))
        ) as client:
            with pytest.raises(httpx2.HTTPStatusError):
                await fetch_model_prices_raw(client=client)

    asyncio.run(run())


def test_cli_awaits_downloader(tmp_path, monkeypatch):
    from tokenary.generator.__main__ import main

    fetch = AsyncMock(return_value={"own-model": {"input_cost_per_token": 0.25}})
    monkeypatch.setattr("tokenary.generator.__main__.fetch_model_prices_raw", fetch)
    output = tmp_path / "prices.json"
    main(
        ["--url", "https://example.test/prices.json", "--all", "--output", str(output)]
    )
    fetch.assert_awaited_once_with(url="https://example.test/prices.json")
    from tokenary import PricingCatalog

    assert (
        PricingCatalog.from_file(output).models["own-model"].input_cost_per_token
        == 0.25
    )


def test_cli_reports_network_errors(tmp_path, monkeypatch, capsys):
    from tokenary.generator.__main__ import main

    fetch = AsyncMock(side_effect=httpx2.ConnectError("offline"))
    monkeypatch.setattr("tokenary.generator.__main__.fetch_model_prices_raw", fetch)
    output = tmp_path / "prices.json"
    with pytest.raises(SystemExit) as exc:
        main(["--all", "--output", str(output)])
    assert exc.value.code == 1
    assert "Generation failed: offline" in capsys.readouterr().err
    assert not output.exists()


def test_write_raw_prices_file_creates_missing_parent_dirs(tmp_path) -> None:
    output_file = tmp_path / "nested" / "catalog.json"

    written_path = write_raw_prices_file(
        raw_prices={"sample_spec": {}, "model-a": {"input_cost_per_token": 0.1}},
        output_path=output_file,
    )

    assert written_path == output_file
    assert output_file.exists()


def test_render_python_catalog_emits_enum_and_lazy_catalog() -> None:
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
    assert "CATALOG = PricingCatalog.from_dict(" in rendered
    assert "calculate" not in rendered
    assert "GeneratedModelPricing(" not in rendered


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

    assert "CATALOG" in generated
    assert "AZURE_GPT_35_TURBO_0125" in generated
    namespace = {"__name__": "test_prices"}
    exec(compile(generated, str(py_path), "exec"), namespace)
    result = calculate(
        model=namespace["ModelName"].AZURE_GPT_35_TURBO_0125,
        input_tokens=100,
        catalog=namespace["CATALOG"],
    )
    assert result.total_cost == pytest.approx(0.0001)
