from tokenary.generator import __main__ as generator_main


def test_cli_main_delegates_to_cli_generate(monkeypatch) -> None:
    called = {"value": False}

    def fake_cli_generate() -> None:
        called["value"] = True

    monkeypatch.setattr("tokenary.generator.__main__.cli_generate", fake_cli_generate)
    generator_main.main()

    assert called["value"] is True
