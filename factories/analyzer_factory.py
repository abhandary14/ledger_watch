"""
AnalyzerFactory — resolves an analyzer type string to an Analyzer instance.

Usage:
    analyzer = AnalyzerFactory.create("large_transaction")
    results  = analyzer.run(organization_id)

New analyzers can be added via AnalyzerFactory.register() without modifying
the factory's core code.
"""

from services.analyzers.base import Analyzer
from services.analyzers.burn_rate import BurnRateAnalyzer
from services.analyzers.duplicate import DuplicateTransactionAnalyzer
from services.analyzers.large_transaction import LargeTransactionAnalyzer
from services.analyzers.vendor_spike import VendorSpikeAnalyzer


class AnalyzerFactory:
    _registry: dict[str, type[Analyzer]] = {
        "large_transaction": LargeTransactionAnalyzer,
        "burn_rate": BurnRateAnalyzer,
        "vendor_spike": VendorSpikeAnalyzer,
        "duplicate": DuplicateTransactionAnalyzer,
    }

    @classmethod
    def create(cls, analyzer_type: str) -> Analyzer:
        klass = cls._registry.get(analyzer_type)
        if not klass:
            raise ValueError(f"Unknown analyzer type: '{analyzer_type}'")
        return klass()

    @classmethod
    def register(cls, name: str, klass: type[Analyzer]) -> None:
        """Register a new analyzer type without modifying the factory core."""
        cls._registry[name] = klass

    @classmethod
    def available(cls) -> list[str]:
        """Return the list of registered analyzer type names."""
        return list(cls._registry.keys())
