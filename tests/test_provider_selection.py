import copy
import json

import pytest

from tokenary import PricingCatalog
from tokenary.generator.__main__ import main
from tokenary.generator.generator import (
    build_catalog_payload,
    render_python_catalog,
    select_models,
)


@pytest.fixture
def prices():
    return {
        "sample_spec": {"litellm_provider": "metadata"},
        "misleading/model-a": {"litellm_provider": "one", "input_cost_per_token": 1},
        "misleading/model.a": {"litellm_provider": "two", "input_cost_per_token": 2},
        "other": {"litellm_provider": "one", "input_cost_per_token": 3},
        "no-provider": {"input_cost_per_token": 4},
    }


@pytest.mark.parametrize(
    "selection, expected",
    [
        ({"providers": ["one"]}, {"misleading/model-a", "other"}),
        (
            {"providers": ["one", "two", "one"]},
            {"misleading/model-a", "misleading/model.a", "other"},
        ),
        ({"models": ["no-provider"]}, {"no-provider"}),
        (
            {
                "providers": ["two"],
                "models": ["misleading/model-a", "misleading/model.a"],
            },
            {"misleading/model.a"},
        ),
        ({}, {"misleading/model-a", "misleading/model.a", "other", "no-provider"}),
    ],
)
def test_provider_and_model_selection_share_the_full_source_names(
    prices, selection, expected
):
    before = copy.deepcopy(prices)
    full = build_catalog_payload(prices)
    payload = build_catalog_payload(prices, **selection)
    assert set(payload["models"]) == expected
    assert set(select_models(prices, **selection)) == expected
    assert payload["enum_names"] == {
        name: full["enum_names"][name] for name in expected
    }
    assert prices == before
    # The Python renderer accepts exactly the same selection.
    namespace = {}
    exec(
        compile(render_python_catalog(prices, **selection), "selected.py", "exec"),
        namespace,
    )
    assert set(namespace["CATALOG"].models) == expected


@pytest.mark.parametrize(
    "selection, message",
    [
        ({"providers": []}, "at least one provider"),
        ({"models": []}, "at least one model"),
        ({"providers": ["One", "metadata", "misleading"]}, "One, metadata, misleading"),
        ({"models": ["sample_spec", "OTHER"]}, "OTHER, sample_spec"),
        ({"providers": ["one"], "models": ["no-provider"]}, "No models match"),
    ],
)
def test_invalid_selections_fail_clearly(prices, selection, message):
    with pytest.raises(ValueError, match=message):
        build_catalog_payload(prices, **selection)


@pytest.mark.parametrize("suffix", [".py", ".json", ".json.gz"])
def test_cli_provider_selection_and_check_use_the_same_models(tmp_path, prices, suffix):
    source = tmp_path / "source.json"
    source.write_text(json.dumps(prices), encoding="utf-8")
    output = tmp_path / f"selected{suffix}"
    args = [
        "--input",
        str(source),
        "--provider",
        "one",
        "--provider",
        "two",
        "--model",
        "misleading/model.a",
        "--output",
        str(output),
    ]
    main(args)
    before = output.read_bytes()
    main([*args, "--check"])
    assert output.read_bytes() == before
    if suffix == ".py":
        namespace = {}
        exec(compile(output.read_bytes(), str(output), "exec"), namespace)
        catalog = namespace["CATALOG"]
    else:
        catalog = PricingCatalog.from_file(output)
    assert set(catalog.models) == {"misleading/model.a"}
    main(["--input", str(source), "--provider", "one", "--output", str(output)])
    if suffix != ".py":
        assert set(PricingCatalog.from_file(output).models) == {
            "misleading/model-a",
            "other",
        }


@pytest.mark.parametrize(
    "selection",
    [["--provider", "missing"], ["--provider", "one", "--model", "no-provider"]],
)
def test_cli_invalid_provider_selection_keeps_output(tmp_path, prices, selection):
    source = tmp_path / "source.json"
    source.write_text(json.dumps(prices), encoding="utf-8")
    output = tmp_path / "keep.json"
    main(["--input", str(source), "--all", "--output", str(output)])
    before = output.read_bytes()
    with pytest.raises(SystemExit) as exc:
        main(["--input", str(source), *selection, "--output", str(output)])
    assert exc.value.code == 1
    assert output.read_bytes() == before


@pytest.mark.parametrize(
    "selection", [["--all", "--provider", "one"], ["--all", "--models", "other"]]
)
def test_all_cannot_be_combined_with_filters_before_download(monkeypatch, selection):
    def unexpected(**kwargs):
        pytest.fail("invalid arguments must not download")

    monkeypatch.setattr(
        "tokenary.generator.__main__.fetch_model_prices_raw", unexpected
    )
    with pytest.raises(SystemExit) as exc:
        main([*selection, "--output", "unused.json"])
    assert exc.value.code == 2
