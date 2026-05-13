from tokenary import cli


def test_cli_main_delegates_to_cli_generate(monkeypatch) -> None:
    called = {"value": False}

    def fake_cli_generate() -> None:
        called["value"] = True

    monkeypatch.setattr("tokenary.cli.cli_generate", fake_cli_generate)
    cli.main()

    assert called["value"] is True