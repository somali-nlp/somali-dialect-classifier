"""
YAML configuration resources for Somali Dialect Classifier.

This sub-package holds environment-specific YAML profiles that complement
the Pydantic-settings runtime configuration in ``somdialc.infra.config``.

Files:
    production.yaml  — production scraping limits, rate limits, observability
    development.yaml — relaxed limits for local development

Usage:
    from importlib.resources import files

    cfg_path = files("somdialc.infra.profiles").joinpath("production.yaml")
    with cfg_path.open() as f:
        data = yaml.safe_load(f)
"""
