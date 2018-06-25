"""A library allowing you to create an auto method-binding dict.

Mainly used for event handlers, a binding dict consists of a mapping between
any events or keys, to their appropriate handler functions within a class.
Upon key lookup, the dict will bind the appropriate function to the instance
of the class.

For an example:

class Server:
    def __init__(self, name):
        self.name = name
    def on_connect(self, remote_host):
        print(self.name, remote_host)
    def on_connect(self, remote_host):
        print(self.name, remote_host)
    handlers = BDict({NewConnectionEvent: on_connect,
    DisconnectonEvent: on_disconnect})

>>> s = Server("myserver")
>>> s.handlers[NewConnectionEvent]("1.2.3.4")
myserver 1.2.3.4

As you can see, after accessing the handlers dict, and upon key lookup,
the dict bound the handler functions to the instance.
"""
__author__ = "Bar Harel"
__version__ = "0.1.0"
__license__ = "MIT"
__all__ = ["BDict"]

from collections import ChainMap as _ChainMap
from itertools import chain as _chain

from typing import (
    Any as _Any, Callable as _Callable, cast as _cast, Dict as _Dict,
    Iterable as _Iterable, Mapping as _Mapping,
    MutableMapping as _MutableMapping, Optional as _Optional,
    overload as _overload, Tuple as _Tuple, Type as _Type, TypeVar as _TypeVar,
    Union as _Union)

from weakref import ref as _ref, WeakKeyDictionary as _WeakKeyDictionary


_T = _TypeVar("_T")
_KT = _TypeVar("_KT")
_VT = _TypeVar("_VT", bound=_Callable)
BDICT_INPUT_TYPE = _Union[_Iterable[_Tuple[_KT, _VT]], _Mapping[_KT, _VT]]


class _custom:
    """Marker for custom value that shouldn't be auto-bound"""
    __slots__ = ("value",)

    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return repr(self.value)


class BDict(_Dict[_KT, _VT]):
    """An auto method-binding dict"""
    __slots__ = ("_instance_data")

    # Holds a mapping between an instance and it's unique custom dictionary
    _instance_data: _WeakKeyDictionary

    class BoundDict(_MutableMapping):
        """A dict bound to an instance

        Accessing the dict results in methods being automatically bound.

        Adding values to the dict adds them to a custom instance dict which
        holds external inserts. Adding external values results in them being
        stored internally inside BDict, allowing you to retain external values
        throughout the instance lifetime.

        Attributes:
            inst: Functions will be autobound to this instance.
        """
        __slots__ = ("inst", "_mapping")
        _deleted = object()

        def __init__(self, inst, bdict, instance_data, _ChainMap=_ChainMap):
            self.inst = inst
            self._mapping = _ChainMap(instance_data, bdict)

        def __repr__(self):
            repr_items = []
            for key, value in self._mapping.items():
                if value.__class__ is _custom:
                    repr_items.append(f"{key!r}: {value!r}")
                else:
                    repr_items.append(f"{key!r}: (autobinding) {value!r}")

            return (f"{self.__class__.__name__}({', '.join(repr_items)})"
                    f" bound to {self.inst!r}")

        def autobind(self, key, value):
            """Add a function that will be autobound"""
            self._mapping[key] = value

        def __getitem__(self, key, _custom=_custom, _deleted=_deleted):
            try:
                value = self._mapping[key]
            except KeyError:
                raise KeyError(key) from None

            if value.__class__ is _custom:
                return value.value

            if value is _deleted:
                raise KeyError(key)

            inst = self.inst
            return value.__get__(inst, inst.__class__)

        def __setitem__(self, key, value):
            self._mapping[key] = _custom(value)

        def __delitem__(self, key, _deleted=_deleted):
            mapping = self._mapping

            try:
                value = self._mapping[key]
            except KeyError:
                raise KeyError(key) from None

            if value is _deleted:
                raise KeyError(key)

            if key not in mapping.parents:
                del mapping[key]
                return

            mapping[key] = _deleted

        def __iter__(self, _deleted=_deleted):
            return (key for key, value in self._mapping.items()
                    if value is not _deleted)

        def __len__(self):
            return sum(1 for key in self)

        def pop(self, key, default=_deleted, _deleted=_deleted,
                _custom=_custom):
            mapping = self._mapping

            value = mapping.get(key, default)

            if value is _deleted:
                if default is _deleted:
                    raise KeyError(key)
                return default

            if key in mapping.parents:
                mapping[key] = _deleted
            else:
                del mapping[key]

            if value.__class__ is _custom:
                return value.value

            inst = self.inst
            return value.__get__(inst, inst.__class__)

        def clear(self):
            self._mapping = _ChainMap()

    class ClassBoundDict(_MutableMapping):
        """Temporary proxy bound to the original class

        Accessing this dict results in binding of methods to the class.
        It is useful mainly for classmethods.

        Attributes:
            bdict: Original BDict to proxy all __getitem__ and __setitem__ to.
            owner: Original class BDict was created in. Methods will be bound
            to this one.
        """
        __slots__ = ("owner", "bdict")

        def __init__(self, owner, bdict):
            self.bdict = bdict
            self.owner = owner

        def autobind(self, key, value):
            """Add a function that will be autobound"""
            self.bdict[key] = value

        def __repr__(self):
            return f"<classbound proxy to {self.bdict!r}>"

        def __getitem__(self, key, _custom=_custom):
            value = self.bdict[key]

            if value.__class__ is _custom:
                return value.value

            return self.bdict[key].__get__(None, self.owner)

        def __setitem__(self, key, value):
            self.bdict[key] = _custom(value)

        def __delitem__(self, key):
            del self.bdict[key]

        def __iter__(self):
            return iter(self.bdict)

        def __len__(self):
            return len(self.bdict)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._instance_data = _WeakKeyDictionary()

    def __repr__(self):
        repr_items = []
        for key, value in self.items():
            if value.__class__ is _custom:
                repr_items.append(f"{key!r}: {value!r}")
            else:
                repr_items.append(f"{key!r}: (autobinding) {value!r}")

        return (f"{self.__class__.__name__}({', '.join(repr_items)})")

    @_overload
    def __get__(self, inst: None, owner: _Type) -> ClassBoundDict:
        ...

    @_overload
    def __get__(self, inst: _T, owner: _Type[_T]) -> BoundDict:
        ...

    def __get__(self, inst, owner, BoundDict=BoundDict,
                ClassBoundDict=ClassBoundDict):

        if inst is None:
            return ClassBoundDict(owner, self)

        bdict = BoundDict(inst, self,
                          self._instance_data.setdefault(inst, {}))

        return bdict
