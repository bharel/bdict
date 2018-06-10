__author__ = "Bar Harel"
__version__ = "0.1.0b"
__license__ = "MIT"
__all__ = ["BDict"]

from typing import (Callable as _Callable, Mapping as _Mapping,
                    Dict as _Dict, cast as _cast,
                    TypeVar as _TypeVar, Any as _Any)
from weakref import ref as _ref

_KT = _TypeVar("_KT")
_VT = _TypeVar("_VT", bound=_Callable)


class BDict(_Dict[_KT, _VT]):
    __slots__ = ("name", "strong")

    class BoundDict(_Dict):
        __slots__ = ("_inst", "external")
        _sentinel = object()

        def __repr__(self):
            try:
                inst = self._inst()
            except AttributeError:
                inst = None

            if inst is None:
                return (f"<Unbound {self.__class__.__name__} "
                        f"mapping to {super().__repr__()}>")

            return (f"<{self.__class__.__name__} bound to {repr(inst)} "
                    f"with the following mapping: {super().__repr__()}>")

        def bind(self, inst: _Any, *, strong: bool=False) -> None:

            # inst=None is special
            if inst is None:
                raise ValueError("Must bind to an instance.")

            if strong:
                self._inst = lambda: inst
            else:
                self._inst = _ref(inst)

        def __getitem__(self, key: _Any, *, _sentinel=_sentinel) -> _Any:
            func = super().__getitem__(key)

            if func is _sentinel:
                return self.external[key]

            try:
                inst = self._inst()
            except AttributeError as exc:
                raise TypeError(f"Unbound {self.__class__.__name__} is not "
                                f"subscriptable. Please bind() first."
                                ) from exc

            if inst is None:
                raise ReferenceError("Please keep a reference "
                                     "to the instance or pass 'strong=True'.")

            return func.__get__(inst, type(inst))

        def __setitem__(self, key: _Any, value: _Any) -> None:
            super().__setitem__(key, self._sentinel)

            try:
                self.external[key] = value
            except AttributeError:
                self.external: _Dict = {}
                self.external[key] = value

    def __init__(self, dict_: _Mapping[_KT, _VT], *,
                 strong: bool=None) -> None:
        super().__init__(dict_)
        self.strong = strong

    def __repr__(self):
        return (f"<Autobinding {self.__class__.__name__} "
                f"mapping to {super().__repr__()}>")

    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, inst, owner,
                BoundDict=BoundDict, bind=BoundDict.bind):

        if inst is None:
            return self

        strong = self.strong

        bdict = BoundDict(self)

        try:
            setattr(inst, self.name, bdict)
            if strong is None: strong = False

        # Class implemented __slots__
        except AttributeError:
            if strong is None: strong = True

        bind(bdict, inst, strong=strong)

        return bdict
