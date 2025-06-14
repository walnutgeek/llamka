import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)


def get_adjust_to_root_modifier(root: Path | None) -> Callable[[Path], Path]:
    if root is None:
        return lambda path: path
    return lambda path: (root / path).absolute()


def modify_path_attributes(
    model: BaseModel,
    path_modifier: Callable[[Path], Path],
) -> None:
    """Recursively find and modify all Path attributes in a BaseModel instance.

    Args:
        model: The BaseModel instance to process
        path_modifier: A function that takes a Path and returns a modified Path
        include_none: Whether to process None values (default: False)
    """

    def recurse_if_base_model(value: Any) -> bool:
        if isinstance(value, BaseModel):
            logger.debug(f"Recursively modifying {type(value)}")
            modify_path_attributes(value, path_modifier)
            return True
        return False

    for field_name in model.model_dump():
        field_value = getattr(model, field_name)
        if isinstance(field_value, Path):
            # Modify the Path attribute
            new_path = path_modifier(field_value)
            logger.debug(f"Modifying {field_name} from {field_value} to {new_path}")
            setattr(model, field_name, path_modifier(field_value))
        elif not recurse_if_base_model(field_value):
            if isinstance(field_value, list):
                # Process lists of BaseModel instances
                for item in field_value:
                    recurse_if_base_model(item)
            elif isinstance(field_value, dict):
                # Process dictionaries with BaseModel values
                for value in field_value.values():
                    recurse_if_base_model(value)
