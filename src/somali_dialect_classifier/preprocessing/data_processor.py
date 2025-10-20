from abc import ABC, abstractmethod
from pathlib import Path


class DataProcessor(ABC):
    """
    Abstract base class for all data processors.
    Defines the essential methods that every data processor (e.g., for downloading, 
    extracting, processing, and saving data) must implement.

    Subclasses must implement:
    - download(): Download the data from a source.
    - extract(): Extract raw data into a usable format.
    - process(): Clean and prepare the data for downstream tasks (e.g., ML model).
    - save(): Save the processed data to a file or storage medium.
    """

    @abstractmethod
    def download(self) -> Path:
        """Download the data from a source."""
        pass

    @abstractmethod
    def extract(self) -> Path:
        """Extract raw data into a usable format."""
        pass

    @abstractmethod
    def process(self) -> Path:
        """Clean and prepare the extracted data."""
        pass

    @abstractmethod
    def save(self, processed_data: str) -> None:
        """Save the processed data."""
        pass


