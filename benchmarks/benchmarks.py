"""ASV benchmarks for Oct2Py, modeled on tests/test_usage.py."""

import numpy as np

from oct2py import Oct2Py


class StartupBenchmarks:
    """Benchmark Oct2Py session startup and teardown."""

    def time_startup(self):
        """Time to start and stop an Oct2Py session."""
        oc = Oct2Py()
        oc.exit()


class EvalBenchmarks:
    """Benchmark Oct2Py.eval() calls."""

    def setup(self):
        self.oc = Oct2Py()

    def teardown(self):
        self.oc.exit()

    def time_scalar(self):
        """eval() returning a scalar."""
        self.oc.eval("mean([[1, 2], [3, 4]])")

    def time_matrix_3x3(self):
        """eval() returning a 3x3 matrix."""
        self.oc.eval("ones(3,3)")

    def time_list_of_exprs(self):
        """eval() with a list of two expressions."""
        self.oc.eval(["zeros(3);", "ones(3);"])

    def time_svd_nout3(self):
        """eval() with svd(), requesting 3 outputs."""
        self.oc.eval("svd(hilb(3))", nout=3)


class FevalBenchmarks:
    """Benchmark Oct2Py.feval() calls."""

    def setup(self):
        self.oc = Oct2Py()

    def teardown(self):
        self.oc.exit()

    def time_ones_scalar(self):
        """feval('ones', 3) returning a 3x3 matrix."""
        self.oc.feval("ones", 3)

    def time_svd(self):
        """feval('svd', matrix) returning singular values."""
        self.oc.feval("svd", np.array([[1, 2], [1, 3]]))

    def time_svd_nout3(self):
        """feval('svd', matrix, nout=3) returning full decomposition."""
        self.oc.feval("svd", np.array([[1, 2], [1, 3]]), nout=3)


class DynamicFunctionBenchmarks:
    """Benchmark dynamic function dispatch via __getattr__."""

    def setup(self):
        self.oc = Oct2Py()

    def teardown(self):
        self.oc.exit()

    def time_ones_1x2(self):
        """Dynamic call: oc.ones(1, 2)."""
        self.oc.ones(1, 2)

    def time_svd_nout3(self):
        """Dynamic call: oc.svd(matrix, nout=3)."""
        self.oc.svd([[1, 2], [1, 3]], nout=3)


class PushPullBenchmarks:
    """Benchmark push() and pull() for data transfer."""

    def setup(self):
        self.oc = Oct2Py()
        self.small = np.ones((3, 3))
        self.medium = np.ones((50, 50))
        self.large = np.ones((200, 200))

    def teardown(self):
        self.oc.exit()

    def time_scalar(self):
        """push/pull a Python int scalar."""
        self.oc.push("x", 42)
        self.oc.pull("x")

    def time_string(self):
        """push/pull a Python string."""
        self.oc.push("s", "hello")
        self.oc.pull("s")

    def time_small_array(self):
        """push/pull a 3x3 float64 ndarray."""
        self.oc.push("arr", self.small)
        self.oc.pull("arr")

    def time_medium_array(self):
        """push/pull a 50x50 float64 ndarray."""
        self.oc.push("arr", self.medium)
        self.oc.pull("arr")

    def time_large_array(self):
        """push/pull a 200x200 float64 ndarray."""
        self.oc.push("arr", self.large)
        self.oc.pull("arr")

    def time_multi_vars(self):
        """push/pull multiple variables in one call."""
        self.oc.push(["a", "b"], ["foo", [1, 2, 3, 4]])
        self.oc.pull(["a", "b"])
