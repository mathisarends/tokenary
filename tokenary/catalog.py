"""Compact offline catalogs with validation only for models actually used."""

import gzip
import json
from collections.abc import Iterator, Mapping
from copy import deepcopy
from dataclasses import dataclass
from enum import StrEnum
from functools import cached_property, lru_cache
from importlib.resources import files
from pathlib import Path

from ._model_names import make_enum_names
from ._serialization import content_hash
from .pricing import ModelPricing

CATALOG_FORMAT_VERSION = 1


@dataclass(frozen=True)
class CatalogMetadata:
    source: str
    source_sha256: str
    catalog_sha256: str


class _LazyPricings(Mapping[str, ModelPricing]):
    def __init__(self, models: Mapping[str, dict[str, object]]) -> None:
        self._raw = deepcopy(dict(models))
        self._validated: dict[str, ModelPricing] = {}

    def __getitem__(self, model: str) -> ModelPricing:
        if model not in self._validated:
            self._validated[model] = ModelPricing.model_validate(self._raw[model])
        return self._validated[model]

    def __iter__(self) -> Iterator[str]:
        return iter(self._raw)

    def __len__(self) -> int:
        return len(self._raw)


class PricingCatalog:
    def __init__(
        self,
        models: Mapping[str, dict[str, object]],
        *,
        enum_names: Mapping[str, str] | None = None,
        metadata: CatalogMetadata | None = None,
    ) -> None:
        self._prices = _LazyPricings(models)
        self.models: Mapping[str, ModelPricing] = self._prices
        self.enum_names = make_enum_names(models, enum_names)
        self.metadata = metadata

    @property
    def loaded_model_count(self) -> int:
        """Number of models validated so far, independent of catalog size."""
        return len(self._prices._validated)

    @cached_property
    def model_enum(self) -> type[StrEnum]:
        return StrEnum(
            "ModelName",
            {alias: model for model, alias in self.enum_names.items()},
            module="tokenary",
        )

    @classmethod
    def from_raw_prices(cls, raw_prices: Mapping[str, object]) -> "PricingCatalog":
        return cls(
            {
                name: data
                for name, data in raw_prices.items()
                if name != "sample_spec" and isinstance(data, dict)
            }
        )

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "PricingCatalog":
        if payload.get("format_version") != CATALOG_FORMAT_VERSION:
            raise ValueError("Unsupported catalog format version")
        models = payload.get("models")
        names = payload.get("enum_names")
        metadata = payload.get("metadata")
        if not isinstance(models, dict) or not isinstance(names, dict):
            raise ValueError("Catalog must contain models and enum_names objects")
        if not isinstance(metadata, dict):
            raise ValueError("Catalog must contain metadata")
        metadata_fields = {"source", "source_sha256", "catalog_sha256"}
        if set(metadata) != metadata_fields or any(
            not isinstance(value, str) for value in metadata.values()
        ):
            raise ValueError(
                "Catalog metadata fields must be source and SHA-256 strings"
            )
        if set(models) != set(names):
            raise ValueError("Catalog model names do not match pricing entries")
        if any(not isinstance(data, dict) for data in models.values()):
            raise ValueError("Catalog pricing entries must be objects")
        actual_hash = content_hash({"models": models, "enum_names": names})
        parsed_metadata = CatalogMetadata(**metadata)
        if actual_hash != parsed_metadata.catalog_sha256:
            raise ValueError("Catalog checksum does not match its contents")
        return cls(models, enum_names=names, metadata=parsed_metadata)

    @classmethod
    def from_file(cls, path: str | Path) -> "PricingCatalog":
        return cls._from_bytes(Path(path).read_bytes())

    @classmethod
    def _from_bytes(cls, content: bytes) -> "PricingCatalog":
        if content.startswith(b"\x1f\x8b"):
            content = gzip.decompress(content)
        payload = json.loads(content)
        if not isinstance(payload, dict):
            raise ValueError("Catalog must be a JSON object")
        return cls.from_dict(payload)


@lru_cache(maxsize=1)
def get_default_catalog() -> PricingCatalog:
    resource = files("tokenary").joinpath("data/catalog.json.gz")
    return PricingCatalog._from_bytes(resource.read_bytes())
