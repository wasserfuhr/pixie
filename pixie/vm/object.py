

class Object(object):
    """ Base Object for all VM objects
    """

    def type(self):
        affirm(False, u".type isn't overloaded")

class TypeRegistry(object):
    def __init__(self):
        self._types = {}
        self._ns_registry = None

    def register_type(self, nm, tp):
        if self._ns_registry is None:
            self._types[nm] = tp
        else:
            self.var_for_type_and_name(nm, tp)

    def var_for_type_and_name(self, nm, tp):
        from pixie.vm.symbol import symbol
        splits = nm.split(u".")
        size = len(splits) - 1
        assert size >= 0
        ns = u".".join(splits[:size])
        name = splits[size]
        var = self._ns_registry.find_or_make(ns).intern_or_make(name)
        var.set_root(tp)
        return var

    def set_registry(self, registry):
        self._ns_registry = registry
        for nm in self._types:
            tp = self._types[nm]
            self.var_for_type_and_name(nm, tp)


    def get_by_name(self, nm, default=None):
        return self._types.get(nm, default)

_type_registry = TypeRegistry()

class Type(Object):
    def __init__(self, name):
        #assert isinstance(name, unicode), u"Type names must be unicode"
        _type_registry.register_type(name, self)
        self._name = name

    def type(self):
        return Type._type



Type._type = Type(u"Type")

class RuntimeException(Object):
    _type = Type(u"pixie.stdlib.RuntimeException")
    def __init__(self, data):
        self._data = data
        self._trace = []

    def type(self):
        return RuntimeException._type

    def __repr__(self):
        import pixie.vm.rt as rt
        s = []
        trace = self._trace[:]
        trace.reverse()
        for x in trace:
            s.append(x.__repr__())
            s.append(u"\n")

        s.extend([u"RuntimeException: " + rt.str(self._data)._str + u"\n"])


        return u"".join(s)

class WrappedException(Exception):
    def __init__(self, ex):
        assert isinstance(ex, RuntimeException)
        self._ex = ex

    def __repr__(self):
        return repr(self._ex)

    def __str__(self):
        return repr(self._ex)

def affirm(val, msg):
    """Works a lot like assert except it throws RuntimeExceptions"""
    assert isinstance(msg, unicode)
    if not val:
        import pixie.vm.rt as rt
        raise WrappedException(RuntimeException(rt.wrap(msg)))


class ErrorInfo(Object):
    _type = Type(u"pixie.stdlib.ErrorInfo")
    def type(self):
        return ErrorInfo._type
    def __init__(self):
        pass

class InterpreterCodeInfo(ErrorInfo):
    def __init__(self, line, line_number, column_number, file):
        self._line = line
        self._line_number = line_number
        self._column_number = column_number
        self._file = file

    def pad_chars(self):
        chrs = []
        for x in range(self._column_number - 1):
            chrs += u" "
        return u"".join(chrs)

    def __repr__(self):
        return u"in " + self._file + u" at " + unicode(str(self._line_number)) \
               + u":" + unicode(str(self._column_number)) + u"\n" \
               + self._line.__repr__() + u"\n" \
               + self.pad_chars() + u"^"

class NativeCodeInfo(ErrorInfo):
    def __init__(self, name):
        self._name = name

    def __repr__(self):
        return u"in internal function " + self._name + u"\n"

class PolymorphicCodeInfo(ErrorInfo):
    def __init__(self, name, tp):
        self._name = name
        self._tp = tp

    def __repr__(self):
        return u"in polymorphic function " + self._name + u" dispatching on " + self._tp._name + u"\n"



class PixieCodeInfo(ErrorInfo):
    def __init__(self, name):
        self._name = name

    def __repr__(self):
        return u"in pixie function " + self._name + u"\n"
