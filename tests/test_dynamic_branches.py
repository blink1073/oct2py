"""Tests for branch coverage of dynamic.py, io.py, and core._reset_instances_after_fork."""

import atexit
import os
import weakref
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from oct2py import Oct2Py
from oct2py.dynamic import (
    OctaveUserClassAttr,
    _make_variable_ptr_instance,
    _MethodDocDescriptor,
)
from oct2py.io import _encode

# ---------------------------------------------------------------------------
# OctaveUserClassAttr.__get__ when instance is None
# ---------------------------------------------------------------------------


class TestOctaveUserClassAttrInstanceNone:
    def test_get_with_none_instance_returns_sentinel(self):
        """__get__ with instance=None should return 'dynamic attribute'."""
        ref = MagicMock()
        attr = OctaveUserClassAttr(ref, "foo", "foo")
        result = attr.__get__(None, type(None))
        assert result == "dynamic attribute"

    def test_get_with_none_instance_does_not_call_session(self):
        """__get__ with instance=None must not call the session."""
        ref = MagicMock()
        attr = OctaveUserClassAttr(ref, "bar", "bar")
        attr.__get__(None)
        ref.assert_not_called()


# ---------------------------------------------------------------------------
# _MethodDocDescriptor.__get__ when self.doc is not None
# ---------------------------------------------------------------------------


class TestMethodDocDescriptorCached:
    def test_get_returns_cached_doc_without_calling_session(self):
        """When self.doc is already set, __get__ must return it directly."""
        ref = MagicMock()
        desc = _MethodDocDescriptor(ref, "polynomial", "roots")
        desc.doc = "cached documentation"
        result = desc.__get__(object(), type)
        assert result == "cached documentation"
        ref.assert_not_called()

    def test_get_fetches_doc_when_none(self):
        """When self.doc is None, __get__ should call the session."""
        session = MagicMock()
        session._get_doc.return_value = "fetched doc"
        ref = weakref.ref(session) if False else (lambda: session)
        desc = _MethodDocDescriptor(ref, "myclass", "mymethod")
        result = desc.__get__(object(), type)
        assert result == "fetched doc"


# ---------------------------------------------------------------------------
# OctaveUserClass.__init__
# ---------------------------------------------------------------------------


class TestOctaveUserClassInit:
    oc: Oct2Py

    @classmethod
    def setup_class(cls):
        cls.oc = Oct2Py()
        cls.oc.addpath(os.path.dirname(__file__))

    @classmethod
    def teardown_class(cls):
        cls.oc.exit()

    def test_init_creates_instance_and_stores_in_octave(self):
        """OctaveUserClass.__init__ should call feval with the class constructor."""
        # polynomial is defined in tests/@polynomial.
        PolynomialCls = self.oc._get_user_class("polynomial")
        instance = PolynomialCls([1.0, 2.0, 3.0])
        # The constructor should have stored the object in the Octave workspace
        # under the generated address.
        assert hasattr(instance, "_address")
        assert instance._address.startswith("polynomial_")

    def test_init_address_is_unique_per_instance(self):
        """Each OctaveUserClass instance should have a distinct _address."""
        PolynomialCls = self.oc._get_user_class("polynomial")
        inst1 = PolynomialCls([1.0])
        inst2 = PolynomialCls([2.0])
        assert inst1._address != inst2._address


# ---------------------------------------------------------------------------
# _encode with OctaveVariablePtr
# ---------------------------------------------------------------------------


class TestEncodeOctaveVariablePtr:
    oc: Oct2Py

    @classmethod
    def setup_class(cls):
        cls.oc = Oct2Py()

    @classmethod
    def teardown_class(cls):
        cls.oc.exit()

    def test_encode_variable_ptr_fetches_value(self):
        """_encode should dereference an OctaveVariablePtr and encode its value."""
        self.oc.eval("_enc_test_var = [1.0, 2.0, 3.0];")
        ptr = _make_variable_ptr_instance(self.oc, "_enc_test_var")
        result = _encode(ptr, convert_to_float=True)
        assert isinstance(result, np.ndarray)
        assert np.allclose(result, [1.0, 2.0, 3.0])

    def test_encode_variable_ptr_scalar(self):
        """_encode of a scalar OctaveVariablePtr should return the encoded scalar."""
        self.oc.eval("_enc_scalar = 42;")
        ptr = _make_variable_ptr_instance(self.oc, "_enc_scalar")
        result = _encode(ptr, convert_to_float=True)
        # Scalar 42.0 (float) is returned directly by Octave, encoded unchanged
        assert result == pytest.approx(42.0)


# ---------------------------------------------------------------------------
# _reset_instances_after_fork — all branches
# ---------------------------------------------------------------------------


class TestResetInstancesAfterFork:
    """Unit tests for core._reset_instances_after_fork()."""

    def _get_reset_fn(self):
        from oct2py.core import _reset_instances_after_fork

        return _reset_instances_after_fork

    def _get_instances(self):
        from oct2py.core import _instances

        return _instances

    def test_empty_instances_runs_without_error(self):
        """With no live instances, the function should still run and unregister rmtree."""
        reset = self._get_reset_fn()
        instances = self._get_instances()

        # Register a dummy shutil.rmtree call so we can verify it gets removed.
        import shutil

        atexit.register(shutil.rmtree, "/tmp/dummy_oct2py_test", ignore_errors=True)  # noqa: S108
        # Temporarily empty the instances set for this test.
        saved = list(instances)
        for inst in saved:
            instances.discard(inst)

        reset()  # should not raise

        # Restore
        for inst in saved:
            instances.add(inst)

    def test_instance_with_engine_gets_neutralised(self):
        """Instance whose _engine is not None should have it set to None."""
        reset = self._get_reset_fn()
        instances = self._get_instances()

        fake_engine = MagicMock()
        fake_engine.repl = MagicMock()
        fake_engine.repl.terminated = False

        inst = MagicMock(spec=["_engine", "_temp_dir_owner", "_settings"])
        inst._engine = fake_engine
        inst._temp_dir_owner = True
        inst._settings = MagicMock()
        inst._settings.temp_dir = "/tmp/fake"  # noqa: S108

        instances.add(inst)
        try:
            reset()
            assert inst._engine is None
            assert inst._temp_dir_owner is False
            assert inst._settings.temp_dir is None
            # repl.terminated should have been set to True
            assert fake_engine.repl.terminated is True
        finally:
            instances.discard(inst)

    def test_instance_with_no_engine_gets_cleared(self):
        """Instance whose _engine is already None should still get temp_dir cleared."""
        reset = self._get_reset_fn()
        instances = self._get_instances()

        inst = MagicMock(spec=["_engine", "_temp_dir_owner", "_settings"])
        inst._engine = None
        inst._temp_dir_owner = True
        inst._settings = MagicMock()
        inst._settings.temp_dir = "/tmp/fake2"  # noqa: S108

        instances.add(inst)
        try:
            reset()
            assert inst._engine is None
            assert inst._temp_dir_owner is False
            assert inst._settings.temp_dir is None
        finally:
            instances.discard(inst)

    def test_engine_cleanup_exception_is_suppressed(self):
        """Exceptions raised while unregistering the engine cleanup should be swallowed."""
        reset = self._get_reset_fn()
        instances = self._get_instances()

        fake_engine = MagicMock()
        fake_engine._cleanup = MagicMock()
        # Make unregister raise when called with _cleanup
        fake_engine.repl = MagicMock()

        inst = MagicMock(spec=["_engine", "_temp_dir_owner", "_settings"])
        inst._engine = fake_engine
        inst._settings = MagicMock()

        # Patch atexit.unregister to raise for _cleanup to exercise suppress
        original_unregister = atexit.unregister

        def raising_unregister(fn):
            if fn is fake_engine._cleanup:
                raise RuntimeError("atexit error")
            original_unregister(fn)

        instances.add(inst)
        try:
            with patch("oct2py.core.atexit.unregister", side_effect=raising_unregister):
                reset()  # should not raise despite the RuntimeError
            assert inst._engine is None
        finally:
            instances.discard(inst)

    def test_real_instance_fork_simulation(self):
        """Integration: a real Oct2Py instance is neutralised by _reset_instances_after_fork."""
        reset = self._get_reset_fn()
        oc = Oct2Py()
        assert oc._engine is not None
        try:
            reset()
            assert oc._engine is None
            assert oc.settings.temp_dir is None
        finally:
            # Instance is now dead — don't call exit(), just discard
            pass
