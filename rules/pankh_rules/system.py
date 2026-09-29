import inspect
from functools import cache
from pathlib import Path
from types import ModuleType

from openfisca_core.taxbenefitsystems import TaxBenefitSystem
from openfisca_core.variables import Variable

from pankh_rules.entities import entities
from pankh_rules.variables import (
    catalogue,
    derived,
    facts,
    nfst,
    nos,
    post_matric,
    pre_matric,
    top_class,
)

PACKAGE_DIR = Path(__file__).resolve().parent
VARIABLE_MODULES = (facts, derived, pre_matric, post_matric, top_class, nfst, nos, catalogue)

# OpenFisca reads these only from a class's own namespace, so values set on our base classes
# (such as the entity and definition period) are copied onto each concrete variable.
_INHERITABLE_ATTRIBUTES = ("value_type", "entity", "definition_period", "default_value")


class PankhSystem(TaxBenefitSystem):
    def __init__(self) -> None:
        super().__init__(entities)
        for module in VARIABLE_MODULES:
            self.add_variables(*concrete_variables(module))
        self.load_parameters(str(PACKAGE_DIR / "parameters"))


def concrete_variables(module: ModuleType) -> list[type[Variable]]:
    """Variables defined in the module itself, skipping imported and private base classes."""
    variables = [
        cls
        for name, cls in inspect.getmembers(module, inspect.isclass)
        if issubclass(cls, Variable)
        and cls.__module__ == module.__name__
        and not name.startswith("_")
    ]
    for cls in variables:
        for attribute in _INHERITABLE_ATTRIBUTES:
            if attribute not in vars(cls) and hasattr(cls, attribute):
                setattr(cls, attribute, getattr(cls, attribute))
    return variables


@cache
def pankh_system() -> PankhSystem:
    """The loaded rules system. Loading is slow, so it happens once per process."""
    return PankhSystem()
