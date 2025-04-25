import base64
import json
import logging
import sys
from inspect import isclass, iscoroutinefunction, isfunction, ismodule
from types import ModuleType
from typing import Any, Self, final

from pydantic import BaseModel
from typing_extensions import override

log = logging.getLogger(__name__)


class GlobalRef:
    """
    >>> ref = GlobalRef('llamka:GlobalRef')
    >>> ref
    GlobalRef('llamka:GlobalRef')
    >>> ref.get_instance().__name__
    'GlobalRef'
    >>> ref.is_module()
    False
    >>> ref.get_module().__name__
    'llamka'
    >>> grgr = GlobalRef(GlobalRef)
    >>> grgr
    GlobalRef('llamka:GlobalRef')
    >>> grgr.get_instance()
    <class 'llamka.GlobalRef'>
    >>> grgr.is_class()
    True
    >>> grgr.is_function()
    False
    >>> grgr.is_module()
    False
    >>> uref = GlobalRef('llamka:')
    >>> uref.is_module()
    True
    >>> uref.get_module().__name__
    'llamka'
    >>> uref = GlobalRef('llamka')
    >>> uref.is_module()
    True
    >>> uref = GlobalRef(uref)
    >>> uref.is_module()
    True
    >>> uref.get_module().__name__
    'llamka'
    >>> uref = GlobalRef(uref.get_module())
    >>> uref.is_module()
    True
    >>> uref.get_module().__name__
    'llamka'
    """

    module: str
    name: str

    def __init__(self, s: Any) -> None:
        if isinstance(s, GlobalRef):
            self.module, self.name = s.module, s.name
        elif ismodule(s):
            self.module, self.name = s.__name__, ""
        elif isclass(s) or isfunction(s):
            self.module, self.name = s.__module__, s.__name__
        else:
            split = s.split(":")
            if len(split) == 1:
                if not (split[0]):
                    raise AssertionError(f"is {repr(s)} empty?")
                split.append("")
            elif len(split) != 2:
                raise AssertionError(f"too many ':' in: {repr(s)}")
            self.module, self.name = split

    @override
    def __str__(self):
        return f"{self.module}:{self.name}"

    @override
    def __repr__(self):
        return f"{self.__class__.__name__}({repr(str(self))})"

    def get_module(self) -> ModuleType:
        return __import__(self.module, fromlist=[""])

    def is_module(self) -> bool:
        return not (self.name)

    def is_class(self) -> bool:
        return not (self.is_module()) and isclass(self.get_instance())

    def is_function(self) -> bool:
        return not (self.is_module()) and isfunction(self.get_instance())

    def is_async(self) -> bool:
        if self.is_module():
            return False
        if self.is_class():
            return iscoroutinefunction(self.get_instance().__call__)
        return iscoroutinefunction(self.get_instance())

    def get_instance(self) -> Any:
        if self.is_module():
            raise AssertionError(f"{repr(self)}.get_module() only")
        attr = getattr(self.get_module(), self.name)
        return attr


@final
class Logic:
    def __init__(self, config: dict[str, Any], default_ref: str | GlobalRef | None = None) -> None:
        config = dict(config)
        try:
            if default_ref is not None:
                ref = GlobalRef(config.pop("ref$", default_ref))
            else:
                ref = GlobalRef(config.pop("ref$"))
            self.async_call = ref.is_async()
            if ref.is_function():
                self.instance = None
                self.call = ref.get_instance()
                assert config == {}, f"Unexpected entries {config}"
            elif ref.is_class():
                cls = ref.get_instance()
                self.call = self.instance = cls(config)
            else:
                raise AssertionError(f"Invalid logic {ref} in config {config}")
        except:
            log.error(f"Error in {config}")
            raise


def get_module(name: str) -> ModuleType:
    """
    >>> type(get_module('llamka'))
    <class 'module'>
    >>> get_module('llamka.c99')
    Traceback (most recent call last):
    ...
    ModuleNotFoundError: No module named 'llamka.c99'
    """
    if name in sys.modules:
        return sys.modules[name]
    return __import__(name, fromlist=[""])


def str_or_none(s: Any) -> str | None:
    return str(s) if s is not None else None


class JsonBase(BaseModel):
    @classmethod
    def dump_schema(cls) -> str:
        return json.dumps(cls.model_json_schema())

    @classmethod
    def from_json(cls, json_str: str) -> Self:
        return cls.model_validate_json(json_str)

    @classmethod
    def from_base64(cls, base64_str: str) -> Self:
        return cls.from_json(base64.b64decode(base64_str).decode())

    def to_base64(self) -> bytes:
        return base64.b64encode(self.model_dump_json().encode("utf8"))


import random
import time
from base64 import b64decode, b64encode


def encode_base64(bb: bytes) -> str:
    return b64encode(bb).decode()


def ensure_bytes(input: str | bytes) -> bytes:
    if isinstance(input, str):
        input = b64decode(input)
    return input


MIN_NON_PRIVILEGED = 1025
MIN_NON_RESERVED = 49152
MAX_PORT = 65535

random.seed(time.time())


def rand_uint(start: int):
    return random.randint(start, MAX_PORT)


def random_port(only_non_reserved: bool = False) -> int:
    """
    Return a random non privileged port number, giving by default higher probability to
    non-reserved port numbers (>=49152).

    >>> defaults = [ MIN_NON_RESERVED <= random_port() for _ in range(1000)]
    >>> non_reserved = [ MIN_NON_RESERVED <= random_port(True) for _ in range(1000)]
    >>> sum(non_reserved)/len(non_reserved)
    1.0
    >>> sum(defaults)/len(defaults) > .7 # usually in range .75 - .78
    True
    """
    if (not only_non_reserved) and random.randint(1, 3) == 3:
        return rand_uint(MIN_NON_PRIVILEGED)
    return rand_uint(MIN_NON_RESERVED)
