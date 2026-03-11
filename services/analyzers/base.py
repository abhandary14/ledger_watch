"""
Abstract base class for all LedgerWatch analyzers.

Every analyzer must implement run(organization_id) and return a results dict.
"""

from abc import ABC, abstractmethod
from uuid import UUID


class Analyzer(ABC):
    @abstractmethod
    def run(self, organization_id: UUID | str) -> dict:
        """
        Run the analysis for the given organization and return a results dict.

        The returned dict must always include at minimum:
            - "analyzer": str  — the analyzer's type identifier
        """
        ...
