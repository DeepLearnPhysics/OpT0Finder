import os

if 'FMATCH_LIBDIR' not in os.environ:
    raise ImportError('FMATCH_LIBDIR environment variable must be defined.')

from ROOT import gInterpreter, gSystem

def _add_root_include_paths():
    """Register header paths needed by ROOT dictionary autoloading."""
    basedir = os.environ.get(
        'FMATCH_BASEDIR',
        os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    )
    incdir = os.environ.get('FMATCH_INCDIR')

    include_paths = [
        incdir,
        os.path.join(incdir, 'flashmatch') if incdir else None,
        os.path.join(incdir, 'flashmatch', 'Base') if incdir else None,
        os.path.join(incdir, 'flashmatch', 'Base', 'FMWKTools') if incdir else None,
        os.path.join(incdir, 'flashmatch', 'GeoAlgo') if incdir else None,
        os.path.join(incdir, 'flashmatch', 'Algorithms') if incdir else None,
        os.path.join(incdir, 'flashmatch', 'PyUtil') if incdir else None,
        os.path.join(basedir, 'flashmatch'),
        os.path.join(basedir, 'flashmatch', 'Base'),
        os.path.join(basedir, 'flashmatch', 'Base', 'FMWKTools'),
        os.path.join(basedir, 'flashmatch', 'GeoAlgo'),
        os.path.join(basedir, 'flashmatch', 'Algorithms'),
        os.path.join(basedir, 'flashmatch', 'PyUtil'),
    ]

    for path in include_paths:
        if path and os.path.isdir(path):
            gInterpreter.AddIncludePath(path)

_add_root_include_paths()
gSystem.Load(os.path.join(os.environ['FMATCH_LIBDIR'], 'libflashmatch.so'))
from ROOT import flashmatch, phot, sim, geoalgo

# Force loading C functions in dict by instantiating a class.
c = flashmatch.FMParams
c = flashmatch.fmatch_load_pyutil

# from .demo import demo
from .toymc import ToyMC
from .rootinput import ROOTInput
from .utils import AnalysisManager
