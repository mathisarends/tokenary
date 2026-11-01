"""Verify an installed wheel in isolation, without Ruff or provider SDKs."""

import asyncio
import importlib.metadata
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory, gettempdir


async def check_live_catalog(root: Path) -> None:
    import httpx2

    from tokenary import LivePricingCatalog, calculate

    fixture = {"fixture/live-model": {"input_cost_per_token": 0.25}}
    calls = 0

    async def handle(request):
        nonlocal calls
        calls += 1
        return httpx2.Response(200, json=fixture)

    async with httpx2.AsyncClient(transport=httpx2.MockTransport(handle)) as client:
        config = dict(
            models=["fixture/live-model"], cache_path=root / "live.json", client=client
        )
        async with LivePricingCatalog(**config) as prices:
            old = await prices.get_catalog()
            assert await prices.get_catalog() is old
            fixture["fixture/live-model"]["input_cost_per_token"] = 0.5
            current = await prices.get_catalog(force_refresh=True)
            assert (
                calculate(
                    model="fixture/live-model", input_tokens=4, catalog=current
                ).total_cost
                == 2
            )
            assert (
                calculate(
                    model="fixture/live-model", input_tokens=4, catalog=old
                ).total_cost
                == 1
            )
        async with LivePricingCatalog(**config) as restarted:
            assert (await restarted.get_catalog()).metadata == current.metadata
            assert calls == 2


def main() -> None:
    reads = []

    def observed_open(event, args):
        if event == "open" and isinstance(args[0], str):
            path = Path(args[0])
            if path.name == "index.json.gz" or path.parent.name == "providers":
                reads.append(path)

    sys.addaudithook(observed_open)
    import tokenary
    from tokenary.catalog import get_default_catalog
    from tokenary.generator.__main__ import main as generate

    assert "site-packages" in tokenary.__file__, tokenary.__file__
    assert importlib.util.find_spec("ruff") is None
    assert importlib.util.find_spec("openai") is None
    assert importlib.util.find_spec("anthropic") is None
    assert get_default_catalog.cache_info().currsize == 0
    assert reads == []
    from tokenary import ModelName

    assert ModelName.GPT_4O == "gpt-4o"
    assert len(reads) == 1 and reads[0].name == "index.json.gz"
    assert get_default_catalog.cache_info().currsize == 0

    installed = importlib.metadata.distribution("tokenary")
    assert any(entry.name == "py.typed" for entry in installed.files)
    sources = [entry for entry in installed.files if entry.suffix == ".py"]
    source_bytes = sum(installed.locate_file(entry).stat().st_size for entry in sources)
    assert source_bytes < 64000, f"Runtime source budget exceeded: {source_bytes}"
    assert not any(entry.name == "_generated.py" for entry in sources)
    assert not any(
        entry.name == "model_prices.generated.json" for entry in installed.files
    )

    with TemporaryDirectory(prefix="tokenary-wheel-smoke-") as directory:
        root = Path(directory).resolve()
        assert root.parent == Path(gettempdir()).resolve()
        console = Path(sys.executable).with_name(
            "tokenary-generate.exe" if sys.platform == "win32" else "tokenary-generate"
        )
        assert console.is_file(), console
        for entry in (
            [str(console)],
            [sys.executable, "-I", "-m", "tokenary.generator"],
        ):
            help_result = subprocess.run(
                [*entry, "--help"], cwd=root, capture_output=True, text=True
            )
            assert help_result.returncode == 0, help_result.stderr
            missing_output = subprocess.run(
                [*entry, "--all"], cwd=root, capture_output=True, text=True
            )
            assert missing_output.returncode == 2, missing_output.stderr
            assert "--output" in missing_output.stderr
            assert list(root.iterdir()) == []
        source = root / "source.json"
        own_model = "fixture/unreleased-chat"
        assert own_model not in ModelName._value2member_map_
        fixture = {
            "sample_spec": {},
            own_model: {
                "litellm_provider": "fixture-a",
                "input_cost_per_token": 0.25,
                "output_cost_per_token": 0.5,
                "cache_read_input_token_cost": 0.125,
            },
            "excluded/same-provider": {
                "litellm_provider": "fixture-a",
                "input_cost_per_token": 1,
            },
            "excluded/other-provider": {
                "litellm_provider": "fixture-b",
                "input_cost_per_token": 2,
            },
        }
        source.write_text(json.dumps(fixture), encoding="utf-8")
        selections = [
            (["--provider", "fixture-a"], {own_model, "excluded/same-provider"}),
            (["--model", own_model], {own_model}),
            (["--provider", "fixture-a", "--models", own_model], {own_model}),
        ]
        subset_sizes = {}
        for label, entry in (
            ("console", [str(console)]),
            ("module", [sys.executable, "-I", "-m", "tokenary.generator"]),
        ):
            for suffix, (selection, expected) in zip(
                (".py", ".json", ".json.gz"), selections, strict=True
            ):
                output = root / f"{label}{suffix}"
                args = ["--input", str(source), *selection, "--output", str(output)]
                subprocess.run([*entry, *args], cwd=root, check=True)
                subprocess.run([*entry, *args, "--check"], cwd=root, check=True)
                # Execute the installed entry function under the read observer too:
                # subprocess resource reads cannot be observed by the parent.
                generate([*args, "--check"])
                assert len(reads) == 1, reads
                if suffix == ".py":
                    spec = importlib.util.spec_from_file_location(
                        f"{label}_prices", output
                    )
                    selected = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(selected)
                    catalog = selected.CATALOG
                    assert {member.value for member in selected.ModelName} == expected
                else:
                    catalog = tokenary.PricingCatalog.from_file(output)
                assert set(catalog.models) == expected
                result = tokenary.calculate(
                    model=own_model,
                    input_tokens=4,
                    output_tokens=2,
                    cached_input_tokens=2,
                    catalog=catalog,
                )
                assert result.total_cost == 1.75
                assert catalog.loaded_model_count == 1
                for excluded in set(fixture) - expected - {"sample_spec"}:
                    try:
                        tokenary.calculate(
                            model=excluded, input_tokens=1, catalog=catalog
                        )
                    except KeyError as exc:
                        assert excluded in str(exc)
                    else:
                        raise AssertionError(f"Unselected model accepted: {excluded}")
                assert get_default_catalog.cache_info().currsize == 0
                assert len(reads) == 1, reads
                subset_sizes[f"{label}{suffix}"] = output.stat().st_size
                before = output.read_bytes()
                failed = subprocess.run(
                    [
                        *entry,
                        "--input",
                        str(source),
                        "--provider",
                        "unknown",
                        "--output",
                        str(output),
                    ],
                    cwd=root,
                    capture_output=True,
                    text=True,
                )
                assert failed.returncode == 1 and "Unknown providers" in failed.stderr
                assert output.read_bytes() == before

        asyncio.run(check_live_catalog(root))
        assert get_default_catalog.cache_info().currsize == 0
        assert len(reads) == 1, reads

    result = tokenary.calculate(model="gpt-4o", input_tokens=1000)
    assert result.total_cost == 0.0025
    assert get_default_catalog().loaded_model_count == 1
    assert len(reads) == 2 and reads[-1].parent.name == "providers"
    tokenary.calculate(model="gpt-4o", input_tokens=1)
    tokenary.calculate(model="o1", input_tokens=1)
    assert len(reads) == 2
    tokenary.calculate(model="claude-sonnet-4-6", input_tokens=1)
    assert len(reads) == 3 and reads[-1] != reads[-2]
    print(f"Installed wheel verified; source={source_bytes} B, subsets={subset_sizes}")


if __name__ == "__main__":
    main()
