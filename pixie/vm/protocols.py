# -*- coding: utf-8 -*-
from pixie.vm.object import Object, Type, _type_registry, WrappedException, RuntimeException, affirm
from pixie.vm.code import BaseCode, PolymorphicFn, wrap_fn, as_var, defprotocol, extend, Protocol, Var, \
                          resize_list, list_copy, returns, get_var_if_defined
import pixie.vm.code as code
from types import MethodType
from pixie.vm.primitives import true, false, nil
import pixie.vm.numbers as numbers
import rpython.rlib.jit as jit
import rpython.rlib.rstacklet as rstacklet
from rpython.rlib.rarithmetic import r_uint


defprotocol("pixie.stdlib", "ISeq", ["-first", "-next"])
defprotocol("pixie.stdlib", "ISeqable", ["-seq"])

defprotocol("pixie.stdlib", "ICounted", ["-count"])

defprotocol("pixie.stdlib", "IIndexed", ["-nth"])

defprotocol("pixie.stdlib", "IPersistentCollection", ["-conj"])

defprotocol("pixie.stdlib", "IObject", ["-hash", "-eq", "-str", "-repr"])
_eq.set_default_fn(wrap_fn(lambda a, b: false))

defprotocol("pixie.stdlib", "IReduce", ["-reduce"])

defprotocol("pixie.stdlib", "IDeref", ["-deref"])

defprotocol("pixie.stdlib", "IReset", ["-reset!"])

defprotocol("pixie.stdlib", "INamed", ["-namespace", "-name"])

defprotocol("pixie.stdlib", "IAssociative", ["-assoc"])

defprotocol("pixie.stdlib", "ILookup", ["-val-at"])

defprotocol("pixie.stdlib", "IMapEntry", ["-key", "-val"])

defprotocol("pixie.stdlib", "IStack", ["-push", "-pop"])

IVector = as_var("pixie.stdlib", "IVector")(Protocol(u"IVector"))

IMap = as_var("pixie.stdlib", "IMap")(Protocol(u"IMap"))

defprotocol("pixie.stdlib", "IMeta", ["-with-meta", "-meta"])

def default_str(x):
    from pixie.vm.string import String

    return rt.wrap(u"<inst " + x.type()._name + u">")

_str.set_default_fn(wrap_fn(default_str))
_repr.set_default_fn(wrap_fn(default_str))

_meta.set_default_fn(wrap_fn(lambda x: nil))

#_first = PolymorphicFn("-first")
#_next = PolymorphicFn("-next")

@as_var("first")
def first(x):
    return rt._first(x)

@as_var("next")
def next(x):
    return rt.seq(rt._next(x))

@as_var("seq")
def seq(x):
    return rt._seq(x)

@as_var("seq?")
def seq_QMARK_(x):
    return true if rt.instance_QMARK_(rt.ISeq.deref(), x) else false


@as_var("type")
def type(x):
    return x.type()

@extend(_str, Type)
def _str(tp):
    import pixie.vm.string as string
    return string.rt.wrap(u"<type " + tp._name + u">")


@extend(_first, nil._type)
def _first(_):
    return nil

@extend(_next, nil._type)
def _next(_):
    return nil

@extend(_seq, nil._type)
def _seq(_):
    return nil

@extend(_count, nil._type)
def _count(_):
    return numbers.zero_int

@extend(_name, Var)
def __name(self):
    import pixie.vm.string as string
    return string.rt.wrap(self._name)

@extend(_namespace, Var)
def __name(self):
    import pixie.vm.string as string
    return string.rt.wrap(self._ns)

@returns(r_uint)
@as_var("hash")
def __hash(x):
    return rt._hash(x)


_count_driver = jit.JitDriver(name="pixie.stdlib.count",
                              greens=["tp"],
                              reds="auto")
@as_var("count")
def count(x):
    acc = 0
    if ICounted.satisfies(rt.type(x)):
        return rt._count(x)
    while True:
        _count_driver.jit_merge_point(tp=rt.type(x))
        if ICounted.satisfies(rt.type(x)):
           return rt._add(rt.wrap(acc), rt._count(x))
        acc += 1
        x = rt.next(rt.seq(x))


@as_var("+")
def add(a, b):
    return rt._add(a, b)

@as_var("meta")
def __meta(a):
    return rt._meta(a)

@as_var("with-meta")
def __with_meta(a, b):
    return rt._with_meta(a, b)

@returns(bool)
@as_var("has-meta?")
def __has_meta(a):
    return true if rt.instance_QMARK_(rt.IMeta.deref(), a) else false

@as_var("conj")
def conj(a, b):
    return rt._conj(a, b)

@as_var("nth")
def nth(a, b):
    return rt._nth(a, b)


@as_var("str")
def str__args(args):
    from pixie.vm.string import String
    acc = []
    for x in args:
        acc.append(rt._str(x)._str)
    return rt.wrap(u"".join(acc))

@as_var("apply")
@jit.unroll_safe
def apply__args(args):
    last_itm = args[len(args) - 1]
    if not rt.instance_QMARK_(rt.IIndexed.deref(), last_itm) or \
        not rt.instance_QMARK_(rt.ICounted.deref(), last_itm):
        raise ValueError("Last item to apply must be bost IIndexed and ICounted")

    fn = args[0]
    argc = r_uint(len(args) - 2)
    out_args = [None] * (argc + r_uint(rt.count(last_itm).int_val()))

    list_copy(args, 1, out_args, 0, argc)

    for x in range(rt.count(last_itm).int_val()):
        out_args[argc + x] = rt.nth(last_itm, rt.wrap(x))

    return fn.invoke(out_args)


@as_var("print")
def _print(a):
    print rt._str(a)._str
    return nil

@returns(bool)
@as_var("instance?")
def _instance(proto, o):
    affirm(isinstance(proto, Protocol), u"proto must be a Protocol")

    return true if proto.satisfies(o.type()) else false


import pixie.vm.rt as rt


@as_var("load_file")
def load_file(filename):
    import pixie.vm.reader as reader
    import pixie.vm.compiler as compiler
    f = open(str(filename._str))
    data = f.read()
    f.close()
    rdr = reader.StringReader(unicode(data))
    result = nil
    while True:
        form = reader.read(rdr, False)
        print "printing"
        print rt.str(form)._str
        if form is reader.eof:
            return result
        print "compiling"
        result = compiler.compile(form).invoke([])
        print "compiled"

@as_var("extend")
def extend(proto_fn, tp, fn):
    affirm(isinstance(proto_fn, PolymorphicFn), u"First argument to extend should be a PolymorphicFn")
    affirm(isinstance(tp, Type), u"Second argument to extend must be a Type")
    affirm(isinstance(fn, BaseCode), u"Last argument to extend must be a function")
    proto_fn.extend(tp, fn)
    return nil

@as_var("type-by-name")
def type_by_name(nm):
    import pixie.vm.string as string
    affirm(isinstance(nm, string.String), u"type name must be string")
    return _type_registry.get_by_name(nm._str, nil)

@as_var("deref")
def deref(x):
    return rt._deref(x)

@as_var("identical?")
def identical(a, b):
    return true if a is b else false

@as_var("vector?")
def vector_QMARK_(a):
    return true if rt.instance_QMARK_(rt.IVector.deref(), a) else false

@returns(bool)
@as_var("eq")
def eq(a, b):
    if a is b:
        return true
    else:
        return rt._eq(a, b)

@as_var("set-macro!")
def set_macro(f):
    affirm(isinstance(f, BaseCode), u"Only code objects can be macros")
    f.set_macro()
    return f

@returns(unicode)
@as_var("name")
def name(s):
    return rt._name(s)

@returns(unicode)
@as_var("namespace")
def namespace(s):
    return rt._namespace(s)

@as_var("-try-catch")
def _try_catch(main_fn, catch_fn, final):
    try:
        return main_fn.invoke([])
    except Exception as ex:
        if not isinstance(ex, WrappedException):
            from pixie.vm.string import String
            if isinstance(ex, Exception):
                ex = RuntimeException(rt.wrap(u"Some error"))
            else:
                ex = RuntimeException(nil)
            return catch_fn.invoke([ex])
        else:
            return catch_fn.invoke([ex._ex])
    finally:
        if final is not nil:
            final.invoke([])

@as_var("throw")
def _throw(ex):
    if isinstance(ex, RuntimeException):
        raise WrappedException(ex)
    raise WrappedException(RuntimeException(ex))

@as_var("resolve")
def _var(nm):
    var = get_var_if_defined(rt.namespace(nm), rt.name(nm), nil)
    return var

@as_var("set-dynamic!")
def set_dynamic(var):
    affirm(isinstance(var, Var), u"set-dynamic! expects a var as an argument")
    var.set_dynamic()
    return var

@as_var("set!")
def set(var, val):
    affirm(isinstance(var, Var), u"Can only set the dynamic value of a var")
    var.set_value(val)
    return var

@as_var("push-binding-frame!")
def push_binding_frame():
    code._dynamic_vars.push_binding_frame()
    return nil

@as_var("pop-binding-frame!")
def pop_binding_frame():
    code._dynamic_vars.pop_binding_frame()
    return nil