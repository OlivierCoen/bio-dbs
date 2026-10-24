import importlib
import inspect
import pkgutil

from .base import Module

def discover_modules() -> list[type[Module]]:
    """
    Find every AbstractModule subclass in this package.
    """
    modules = []
    package = importlib.import_module("modules")
    for mod in pkgutil.iter_modules(package.__path__):
        module = importlib.import_module(f"modules.{mod.name}")
        for _, cls in inspect.getmembers(module):
            if issubclass(cls, Module) and not inspect.isabstract(cls):
                modules.append(cls)
    return modules