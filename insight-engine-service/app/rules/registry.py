"""Dynamic rule discovery.

Walks the category subpackages (cost/, performance/, …) and collects every
module-level `RULE`. Adding a rule = drop a module that defines `RULE`; no
registration wiring needed.
"""
import importlib
import logging
import pkgutil

from .base import Rule

logger = logging.getLogger("insight-engine")

CATEGORIES = [
    "cost",
    "performance",
    "reliability",
    "availability",
    "security",
    "compliance",
    "storage",
]

_cache: list[Rule] | None = None


def load_rules() -> list[Rule]:
    rules: list[Rule] = []
    for category in CATEGORIES:
        pkg_name = f"{__package__}.{category}"
        try:
            catpkg = importlib.import_module(pkg_name)
        except ModuleNotFoundError:
            continue
        for modinfo in pkgutil.iter_modules(catpkg.__path__):
            mod = importlib.import_module(f"{pkg_name}.{modinfo.name}")
            rule = getattr(mod, "RULE", None)
            if rule is not None:
                rules.append(rule)
    logger.info("Loaded %s rules across %s categories", len(rules), len(CATEGORIES))
    return rules


def get_rules() -> list[Rule]:
    global _cache
    if _cache is None:
        _cache = load_rules()
    return _cache
