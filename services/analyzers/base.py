"""
Abstract base class for all LedgerWatch analyzers.

Every analyzer must implement run() and return a results dict.
Tenant isolation is provided by the active PostgreSQL schema on the connection.
"""

from abc import ABC, abstractmethod


class Analyzer(ABC):
    @abstractmethod
    def run(self) -> dict:
        """
        Run the analysis against the current tenant schema and return a results dict.

        The returned dict must always include at minimum:
            - "analyzer": str  — the analyzer's type identifier
        """
        ...
