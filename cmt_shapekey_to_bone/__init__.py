from . import panels, properties, operations

from ..registration import register_modules, unregister_modules

modules = [panels, properties, operations]


def register() -> None:
    register_modules(modules)


def unregister() -> None:
    unregister_modules(modules)


if __name__ == "__main__":
    register()
