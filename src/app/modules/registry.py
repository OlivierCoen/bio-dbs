import importlib
import inspect
import pkgutil
import logging

from .base import BaseModule

logger = logging.getLogger(__name__)


def discover_modules() -> dict[str, type[BaseModule]]:
    package = importlib.import_module("modules")
    found: dict[str, type[BaseModule]] = {}

    for info in pkgutil.walk_packages(package.__path__, prefix="modules."):
        module = importlib.import_module(info.name)
        for name, cls in inspect.getmembers(module, inspect.isclass):
            if (
                cls.__module__ == module.__name__ 
                and issubclass(cls, BaseModule)
                and cls is not BaseModule
                and not inspect.isabstract(cls)
            ):
                found[cls.NAME] = cls

    return found
