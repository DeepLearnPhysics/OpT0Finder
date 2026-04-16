import atexit
import os
import sys

if 'FMATCH_LIBDIR' not in os.environ:
    raise ImportError('FMATCH_LIBDIR environment variable must be defined.')

from ROOT import gInterpreter, gROOT, gSystem


def _package_basedir():
    return os.environ.get(
        'FMATCH_BASEDIR',
        os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    )


def _add_root_include_paths():
    """Register paths needed by ROOT dictionary payload autoloading."""
    basedir = _package_basedir()
    incdir = os.environ.get('FMATCH_INCDIR')

    include_paths = [
        incdir,
        os.path.join(incdir, 'flashmatch', 'Base') if incdir else None,
        os.path.join(incdir, 'flashmatch', 'Base', 'FMWKTools') if incdir else None,
        os.path.join(incdir, 'flashmatch', 'GeoAlgo') if incdir else None,
        os.path.join(incdir, 'flashmatch', 'Algorithm') if incdir else None,
        os.path.join(incdir, 'flashmatch', 'core', 'PyUtil') if incdir else None,
        os.path.join(basedir, 'flashmatch', 'Base'),
        os.path.join(basedir, 'flashmatch', 'Base', 'FMWKTools'),
        os.path.join(basedir, 'flashmatch', 'GeoAlgo'),
        os.path.join(basedir, 'flashmatch', 'Algorithms'),
        os.path.join(basedir, 'flashmatch', 'PyUtil'),
    ]

    for path in include_paths:
        if path and os.path.isdir(path):
            gInterpreter.AddIncludePath(path)


def _root_version_at_least(major, minor):
    version = gROOT.GetVersion().split('/')[0]
    parts = version.split('.')
    try:
        return (int(parts[0]), int(parts[1])) >= (major, minor)
    except (IndexError, ValueError):
        return False


def _install_root_shutdown_bypass():
    """Bypass ROOT shutdown only for the known larcv/flashmatch collision."""
    mode = os.environ.get('FMATCH_BYPASS_ROOT_SHUTDOWN', 'auto').lower()
    if mode in ('0', 'false', 'no', 'off'):
        return
    if mode == 'auto' and ('larcv' not in sys.modules or not _root_version_at_least(6, 30)):
        return

    exit_status = {'code': 0}
    previous_excepthook = sys.excepthook

    def recording_excepthook(exc_type, exc, tb):
        exit_status['code'] = 1
        previous_excepthook(exc_type, exc, tb)

    def recording_exit(code=0):
        if code is None:
            exit_status['code'] = 0
        else:
            try:
                exit_status['code'] = int(code)
            except (TypeError, ValueError):
                exit_status['code'] = 1
        raise SystemExit(code)

    def hard_exit_before_root_cleanup():
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(exit_status['code'])

    sys.excepthook = recording_excepthook
    sys.exit = recording_exit
    atexit.register(hard_exit_before_root_cleanup)


_add_root_include_paths()
gSystem.Load(os.path.join(os.environ['FMATCH_LIBDIR'], 'libflashmatch.so'))
from ROOT import flashmatch as _root_flashmatch, phot, sim, geoalgo
_install_root_shutdown_bypass()

# Force-load the configuration dictionary used by ROOTInput/AnalysisManager.
# Do not force-load fmatch_load_pyutil here: loading OpT0Finder's copied PyUtil
# dictionary together with larcv's PyUtil dictionary corrupts ROOT 6.30/6.32
# interpreter shutdown. The small PyUtil helpers used by Python code are
# reimplemented below to keep the public API available without that dictionary.
c = _root_flashmatch.FMParams


def _sequence_size(obj):
    if hasattr(obj, 'size'):
        return obj.size()
    return len(obj)


def _as_numpy_vector(obj):
    import numpy as np

    return np.asarray([obj[i] for i in range(_sequence_size(obj))])


def _as_geoalgo_trajectory(points):
    import numpy as np

    points = np.asarray(points, dtype=np.float64)
    if points.ndim != 2:
        raise ValueError('as_geoalgo_trajectory expects a 2D array')

    traj = geoalgo.Trajectory(points.shape[0], points.shape[1])
    for i in range(points.shape[0]):
        for j in range(points.shape[1]):
            traj[i][j] = float(points[i, j])
    return traj


def _as_ndarray(obj):
    import numpy as np

    if hasattr(obj, 'pe_v'):
        return _as_numpy_vector(obj.pe_v).astype(np.float64, copy=False)

    size = _sequence_size(obj)
    if size == 0:
        return np.empty((0, 0), dtype=np.float64)

    first = obj[0]
    if all(hasattr(first, attr) for attr in ('x', 'y', 'z', 'q')):
        return np.asarray(
            [[obj[i].x, obj[i].y, obj[i].z, obj[i].q] for i in range(size)],
            dtype=np.float64
        )

    return np.asarray(
        [[obj[i][j] for j in range(_sequence_size(obj[i]))] for i in range(size)],
        dtype=np.float64
    )


def _copy_array(arrayin, cvec):
    arrayin[...] = _as_numpy_vector(cvec).reshape(arrayin.shape)


class _DetectorSpecs:
    """Small Python facade around the ROOT DetectorSpecs singleton."""

    _configured = False

    def __call__(self, *args):
        return _root_flashmatch.DetectorSpecs(*args)

    def __getattr__(self, name):
        return getattr(_root_flashmatch.DetectorSpecs, name)

    def GetME(self, *args):
        if not args and not self._configured:
            # Avoid throwing the unconfigured C++ singleton exception through
            # cppyy. In ROOT 6.30/6.32 with larcv loaded, that leaves ROOT in a
            # bad shutdown state even when Python catches the exception.
            raise RuntimeError(
                'DetectorSpecs::GetME() called before DetectorSpecs was configured'
            )
        result = _root_flashmatch.DetectorSpecs.GetME(*args)
        if args:
            self._configured = True
        return result


class _FlashMatchNamespace:
    """Proxy ROOT.flashmatch while overriding fragile Python-facing pieces."""

    DetectorSpecs = _DetectorSpecs()
    as_geoalgo_trajectory = staticmethod(_as_geoalgo_trajectory)
    as_ndarray = staticmethod(_as_ndarray)
    copy_array = staticmethod(_copy_array)

    def __getattr__(self, name):
        return getattr(_root_flashmatch, name)


flashmatch = _FlashMatchNamespace()
# from .demo import demo
from .toymc import ToyMC
from .rootinput import ROOTInput
from .utils import AnalysisManager
