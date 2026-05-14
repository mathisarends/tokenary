import json
import pytest

from tokenary.generator.downloader import fetch_model_prices_raw, write_raw_prices_file


class _FakeResponse:
    def __init__(self, payload: str) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return self._payload.encode("utf-8")

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_fetch_model_prices_raw_success(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = json.dumps({"sample_spec": {}, "my-model": {"mode": "chat"}})

    def fake_urlopen(request, timeout=30):
        assert timeout == 30
        assert request.full_url == "https://example.test/prices.json"
        return _FakeResponse(payload)

    monkeypatch.setattr("tokenary.generator.downloader.urlopen", fake_urlopen)

    result = fetch_model_prices_raw(url="https://example.test/prices.json")
    assert result["my-model"]["mode"] == "chat"


def test_fetch_model_prices_raw_rejects_non_object(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_urlopen(request, timeout=30):
        return _FakeResponse("[]")

    monkeypatch.setattr("tokenary.generator.downloader.urlopen", fake_urlopen)

    with pytest.raises(ValueError, match="not a JSON object"):
        fetch_model_prices_raw(url="https://example.test/prices.json")


def test_write_raw_prices_file_creates_parent_dirs(tmp_path) -> None:
    output_file = tmp_path / "nested" / "catalog.json"

    written_path = write_raw_prices_file(
        raw_prices={"sample_spec": {}, "model-a": {"input_cost_per_token": 0.1}},
        output_path=output_file,
    )

    assert written_path == output_file
    assert output_file.exists()
    parsed = json.loads(output_file.read_text(encoding="utf-8"))
    assert parsed["model-a"]["input_cost_per_token"] == 0.1
