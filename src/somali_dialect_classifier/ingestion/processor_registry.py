"""
Processor Registry for dynamic processor discovery and instantiation.

Implements the Registry pattern to decouple orchestration from processor implementations,
enabling plugin-style architecture for adding new data sources.

Design Pattern: Registry + Factory
- Processors self-register via decorator
- Orchestration code queries registry by name
- Open/Closed Principle: Add processors without modifying orchestration
"""

from typing import Any, Callable, Optional

from .base_pipeline import BasePipeline


class ProcessorRegistry:
    """
    Factory for processor discovery and instantiation.

    Usage:
        # Register a processor (usually via decorator)
        ProcessorRegistry.register("wikipedia", WikipediaSomaliProcessor)

        # Create processor instance
        processor = ProcessorRegistry.create("wikipedia", force=True)

        # List all available processors
        sources = ProcessorRegistry.list_processors()
    """

    _processors: dict[str, type[BasePipeline]] = {}

    @classmethod
    def register(cls, name: str, processor_class: type[BasePipeline]) -> None:
        """
        Register a processor class.

        Args:
            name: Unique processor name (e.g., "wikipedia", "bbc")
            processor_class: Class that extends BasePipeline

        Raises:
            ValueError: If name already registered or processor doesn't extend BasePipeline
        """
        if name in cls._processors:
            raise ValueError(f"Processor '{name}' already registered")

        if not issubclass(processor_class, BasePipeline):
            raise ValueError(
                f"Processor class must extend BasePipeline, got {processor_class.__name__}"
            )

        cls._processors[name] = processor_class

    @classmethod
    def create(cls, name: str, **kwargs: Any) -> BasePipeline:
        """
        Create processor instance by name.

        Args:
            name: Registered processor name
            **kwargs: Arguments passed to processor constructor

        Returns:
            Initialized processor instance

        Raises:
            ValueError: If processor name not registered
        """
        if name not in cls._processors:
            available = ", ".join(cls.list_processors())
            raise ValueError(
                f"Unknown processor: '{name}'. Available: {available}"
            )

        processor_class = cls._processors[name]
        return processor_class(**kwargs)

    @classmethod
    def list_processors(cls) -> list[str]:
        """
        List all registered processor names.

        Returns:
            Sorted list of processor names
        """
        return sorted(cls._processors.keys())

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """
        Check if processor name is registered.

        Args:
            name: Processor name to check

        Returns:
            True if registered, False otherwise
        """
        return name in cls._processors

    @classmethod
    def clear_registry(cls) -> None:
        """
        Clear all registered processors.

        WARNING: Only use for testing. This will remove all processor registrations.
        """
        cls._processors.clear()

    @classmethod
    def get_processor_class(cls, name: str) -> Optional[type[BasePipeline]]:
        """
        Get processor class by name without instantiating.

        Args:
            name: Registered processor name

        Returns:
            Processor class or None if not registered
        """
        return cls._processors.get(name)


def register_processor(name: str) -> Callable[[type[BasePipeline]], type[BasePipeline]]:
    """
    Decorator to auto-register processors.

    Usage:
        @register_processor("wikipedia")
        class WikipediaSomaliProcessor(BasePipeline):
            ...

    Args:
        name: Unique processor name

    Returns:
        Decorator function that registers the class
    """
    def decorator(cls: type[BasePipeline]) -> type[BasePipeline]:
        ProcessorRegistry.register(name, cls)
        return cls
    return decorator
