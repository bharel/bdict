# bdict
A library allowing you to create an auto method-binding dict.

Ever dreamed of writing clean dicts pointing keys to methods? Fear no more!

Mainly used for event handlers, a binding dict consists of a mapping between
any events or keys, to their appropriate handler functions within a class.
Upon key lookup, the dict will bind the appropriate function to the instance
of the class.

For an example:

```Python
class Server:
    """Typical server with a small mapping between event handlers and functions"""
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
```
As you can see, after accessing the handlers dict, and upon key lookup,
the dict bound the handler functions to the instance.

BDict also works with classmethods in a clean and fashioned way:

```Python
class MyClass:
    """Typical server with a small mapping between event handlers and functions"""            
    @classmethod
    def class_handle(cls):
        print(cls.__name__)

    handlers = BDict({"class_handle": class_handle})

>>> MyClass.handlers["class_handle"]
<bound method MyClass.class_handle of <class '__main__.MyClass'>>
>>> MyClass.handlers["class_handle"]()
MyClass

>>> inst = MyClass()
>>> inst.handlers["class_handle"]
<bound method MyClass.class_handle of <class '__main__.MyClass'>>
>>> inst.handlers["class_handle"]()
MyClass
```
Upon accessing the BDict through an instance, the BDict will create an internal instance data container on the BDict, 
allowing you to modify it's dictionary and not affect other instances!
```Python
>>> inst.handlers[123] = 456
>>> inst.handlers[123]
456
>>> inst2 = MyClass()
>>> inst2.handlers[123]
Traceback (most recent call last):
  ...
KeyError: 123
```

## Usage:

`BDict(dict_)`

`dict_` can be a dict or an iterable of (key, value) pairs and will be used to initialize `BDict`.

The class BDict is used on must support weak referencing (the vast majority of custom objects do). If you use `__slots__`, you are able to do this by adding `__weakref__` to the slots.
