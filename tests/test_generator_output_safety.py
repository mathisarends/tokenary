import json

import pytest

from tokenary.generator.__main__ import main


@pytest.mark.parametrize(
    "arguments,exit_code",
    [
        (["--all"], 2),
        (["--all", "--check"], 2),
        (["--all", "--output", "bad.txt"], 2),
        (["--all", "--provider", "openai", "--output", "unused.json"], 2),
        (["--help"], 0),
    ],
)
def test_argument_errors_and_help_have_no_io(monkeypatch, arguments, exit_code):
    def unexpected(*args, **kwargs):
        pytest.fail("argument handling must not download, load a catalog or write")

    for name in ("fetch_model_prices_raw", "get_bundled_enum_names", "write_atomic"):
        monkeypatch.setattr(f"tokenary.generator.__main__.{name}", unexpected)
    monkeypatch.setattr("pathlib.Path.read_text", unexpected)
    with pytest.raises(SystemExit) as exc:
        main(arguments)
    assert exc.value.code == exit_code


def test_replace_failure_keeps_existing_output_and_removes_temporary_file(
    tmp_path, monkeypatch, capsys
):
    source = tmp_path / "source.json"
    source.write_text(
        json.dumps({"own": {"input_cost_per_token": 1}}), encoding="utf-8"
    )
    target = tmp_path / "prices.json"
    args = ["--input", str(source), "--all", "--output", str(target)]
    main(args)
    before = target.read_bytes()
    files_before = set(tmp_path.iterdir())

    def failed_replace(*args):
        raise PermissionError("simulated replacement failure")

    monkeypatch.setattr("tokenary._serialization.os.replace", failed_replace)
    with pytest.raises(SystemExit) as exc:
        main(args)
    assert exc.value.code == 1
    assert "simulated replacement failure" in capsys.readouterr().err
    assert target.read_bytes() == before
    assert set(tmp_path.iterdir()) == files_before
