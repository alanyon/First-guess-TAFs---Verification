"""Minimal ``pkg_resources`` compatibility shim.

setuptools >= 81 (used by scitools/production-os48-1 and later) no longer
ships the legacy ``pkg_resources`` module.  VerPy still imports
``resource_filename`` from it in ``VerPy/constants.py``.  This shim provides
just that function so VerPy imports cleanly under the newer environment,
without needing to modify the (read-only) shared VerPy installation.

It is placed on PYTHONPATH via setup_constants.sh.  It is only picked up when
the real ``pkg_resources`` is absent, so it does not shadow a genuine install.
"""

import importlib.util
import os


def resource_filename(package_or_requirement, resource_name):
    """Return the absolute path to a resource bundled inside a package.

    Mirrors ``pkg_resources.resource_filename`` for the simple, source-tree
    case that VerPy relies on: locate the package directory and join the
    (forward-slash separated) resource path onto it.
    """
    spec = importlib.util.find_spec(package_or_requirement)
    if spec is None:
        raise ModuleNotFoundError(
            "No module named {!r}".format(package_or_requirement))

    if spec.submodule_search_locations:
        base = list(spec.submodule_search_locations)[0]
    elif spec.origin:
        base = os.path.dirname(spec.origin)
    else:
        base = os.getcwd()

    return os.path.join(base, *resource_name.split('/'))
