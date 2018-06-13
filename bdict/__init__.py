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


class BDict(_Dict[_KT, _VT]):
    """An auto method-binding dict

    Attributes:
        name: The name BDict will show up in the instance dict. Should be
        the same as the name it's defined with on the class.
        strong: Whether to strong reference or not. See __init__ for
        more explanation.
        autocache: Whether the newly created BDict will be cached on top of
        the instance. Results in faster access, but with a few caveats. See
        __init__ for more explanation.
    """
    __slots__ = ("name", "strong", "_instance_externals", "autocache")
    strong: _Optional[bool]
    name: str

    # Instance externals holds a mapping between an instance and it's externals
    # dictionary. In case of a non-cached BDict, this is the only way of
    # retaining external values accross the instance's numerous BoundDicts.
    _instance_externals: _WeakKeyDictionary

    class BoundDict(_Dict):
        """A dict bound to an instance

        This dict might be cached on top of the instance, or it might exist
        for a limited amount of time non-related to the instance existence.

        Accessing the dict results in methods being automatically bound.

        Adding values to the dict adds them to the "external" dict which holds
        external inserts. If the dict is not stored on top of the instance,
        adding external values results in them being stored internally inside
        BDict, allowing you to retain external values throughout the instance
        lifetime.

        Attributes:
            external: dict of external attributes inserted dynamically on
            top of the BoundDict.
        """
        __slots__ = ("_inst", "external")
        external: _Dict

        _sentinel = object()

        def __repr__(self):
            try:
                inst = self._inst()
            except AttributeError:
                inst = None

            if inst is None:
                return (f"<Unbound {self.__class__.__name__}>")

            return (f"<{self.__class__.__name__} bound to {inst!r}>")

        def bind(self, inst: _Any, *,
                 external: _Dict = None, strong: bool = False) -> None:
            """Bind the BoundDict to the given instance.

            Args:
                inst: Instance to bind it to. Accessing methods will cause them
                to auto-bind to this instance. Can be anything but None.
                external: Externally entered values. Used internally.
                strong: Whether to strong-reference the instance or only weakly
                reference it.
            """
            # Can bind to any type of instance but None.
            # None marks class-access in __get__, and an unbound BoundDict
            # during initialization.
            if inst is None:
                raise ValueError("Must bind to an instance.")

            if external is not None:
                self.external = external

            if strong:
                self._inst = lambda: inst
            else:
                self._inst = _ref(inst)

        def __getitem__(self, key: _Any, *, _sentinel=_sentinel) -> _Any:
            try:
                func = super().__getitem__(key)
            except KeyError:
                external = getattr(self, "external", None)
                if not external or key not in external:
                    raise
                super().__setitem__(key, _sentinel)
                func = _sentinel

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
                                     "to the instance or pass 'strong=True'"
                                     "to BDict.")

            return func.__get__(inst, type(inst))

        def __setitem__(self, key: _Any, value: _Any, *,
                        _sentinel=_sentinel) -> None:
            # Still initializing (pre-bind)
            if self._inst is None:
                super().__setitem__(key, value)

            super().__setitem__(key, _sentinel)

            try:
                self.external[key] = value
            except AttributeError:
                self.external = {}
                self.external[key] = value

        def __delitem__(self, key: _Any) -> None:
            super().__delitem__(key)
            self.external.pop(key, None)

    class ClassBoundDict(_MutableMapping):
        """Temporary proxy bound to the original class

        Accessing this dict results in binding of methods to the class.
        It is useful mainly for classmethods.

        Attributes:
            bdict: Original BDict to proxy all __getitem__ and __setitem__ to.
            owner: Original class BDict was created in. Methods will be bound
            to this one.
        """
        __slots__ = ("bdict", "owner")

        def __init__(self, bdict, owner):
            self.bdict = bdict
            self.owner = owner

        def __repr__(self):
            return f"<classbound proxy to {self.bdict!r}>"

        def __getitem__(self, key):
            return self.bdict[key].__get__(None, self.owner)

        def __setitem__(self, key, value):
            self.bdict[key] = value

        def __delitem__(self, key):
            del self.bdict[key]

        def __iter__(self):
            return iter(self.bdict)

        def __len__(self):
            return len(self.bdict)

    def __init__(self, dict_: BDICT_INPUT_TYPE[_KT, _VT], *,
                 strong: bool = None, autocache: bool = True) -> None:
        """Initialize the auto method-binding dict

        Args:
            dict: Any mapping between keys to class functions
            strong: Whether to strongly reference instances upon dict
            creation or only weakly reference. By default, a weak reference
            will be created in order to avoid a reference cycle. Unless forced
            using 'strong=False', in case of a class which defines __slots__,
            the dict will be created with a strong reference as __slots__
            create caching issues.
            Reference to class'es BDict will always be strongly referenced.
            autocache: Upon access, will automatically cache the BoundDict
            on the instance. On classes with __slots__ it's suggested to
            turn this off as it will not work either case.
        """
        super().__init__(_cast(_Mapping[_KT, _VT], dict_))
        self.strong = strong
        self.autocache = autocache

    def __repr__(self):
        return (f"<Autobinding {self.__class__.__name__}>")

    def __set_name__(self, owner, name):
        self.name = name

    @_overload
    def __get__(self, inst: None, owner: _Type) -> ClassBoundDict:
        ...

    @_overload
    def __get__(self, inst: _T, owner: _Type[_T]) -> BoundDict:
        ...

    def __get__(self, inst, owner,
                BoundDict=BoundDict, bind=BoundDict.bind):

        if inst is None:
            return self.ClassBoundDict(self, owner)

        strong = self.strong

        # Keep in mind it also copies the dict!
        bdict = BoundDict(self)

        # Check if instance externals already exist for this instance
        externals = getattr(self, "_instance_externals", None)
        if externals and inst in externals:
            # Shortcut - Bind straight away and send off
            bind(bdict, strong=True if strong is None else strong,
                 external=externals[inst])
            return bdict

        try:
            # If autocache is enabled
            if self.autocache:

                # Attempt to bind to instance
                setattr(inst, self.name, bdict)

                # Instance bound, no need for external dict
                use_external = False

            # Must use external as we need to store the dict's
            # changes externally (dict is not located on instance)
            else:
                use_external = True

        # Class implemented __slots__, failed binding to instance
        except AttributeError:
            # Must use external (as we cannot autocache).
            use_external = True

        if use_external:
            # Should attempt to strong ref in order not to lose the external
            # dict
            if strong is None: strong = True

            # Create _instance_externals if one does not exist
            if externals is None:
                externals = self._instance_externals = _WeakKeyDictionary()

            # Get the appropriate external and bind
            external: _Dict

            try:
                # Keep in mind - local variable "external" is set even if
                # TypeError is thrown.
                external = externals[inst] = {}
            except TypeError:
                # Instance has __slots__ without __weakref__
                import warnings
                msg = (
                    f"Cannot create a weak reference to "
                    f"'{inst.__class__.__name__}' object. Changes to BoundDict"
                    f" will not be shared accross the instance!")
                warnings.warn(msg)

            bind(bdict, inst, strong=strong, external=external)

        else:
            # Weakref is fine
            if strong is None: strong = False
            bind(bdict, inst, strong=strong)

        return bdict
