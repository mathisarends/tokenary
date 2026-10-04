class MissingPriceError(ValueError):
    """A requested usage category has no supported price in the selected catalog."""

    def __init__(self, model: str, price_field: str) -> None:
        self.model = model
        self.price_field = price_field
        super().__init__(f"Model {model!r} has no supported price for {price_field!r}")


class UnsupportedUsageError(ValueError):
    """Provider usage cannot be unambiguously mapped to supported billing units."""
