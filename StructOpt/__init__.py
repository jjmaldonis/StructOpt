"""Functions for use in optimizer"""

try:
    import ase
except ImportError:
    raise ImportError("ASE must be installed to use Structopt.")

from . import fileio
from . import crossover
from . import fingerprinting
from . import fitness
from . import generate
from . import moves
from . import post_processing
from . import predator
from . import relaxations
from . import selection
from . import switches
from . import tools

# See https://github.com/mpi4py/mpi4py/blob/4b22c6c8ed73cd8eabdaa60a3cec0b804c1036cb/demo/init-fini/test_1.py
#from mpi4py import rc
#rc.initialize = False

def setup(input):
    import time
    import logging
    parameters = fileio.read_parameter_input(input)
    if parameters["USE_MPI4PY"]:
        try:
            from mpi4py import MPI
        except ImportError:
            raise ImportError("mpi4py must be installed to use StructOpt.")
        parameters["rank"] = MPI.COMM_WORLD.Get_rank()
    else:
        parameters["rank"] = 0

    logging_level = parameters.get("logging_level", "info")
    logging_level = getattr(logging, logging_level.upper())

    if "loggername" not in parameters:
        parameters["loggername"] = "{0}-rank{1}-{2}.log".format(parameters["filename"], parameters["rank"], time.strftime("%Y_%m%d_%H%M%S"))
    else:
        raise ValueError("'loggername' should not be defined in the input file currently. If you think you want to define it, talk to the developers about why.")

    if parameters["rank"] == 0:
        logger = fileio.logger_utils.initialize_logger(filename=parameters["loggername"], name="default", level=logging_level)
        if logging_level <= logging.DEBUG:
            debug_logger = fileio.logger_utils.initialize_logger(filename=parameters["loggername"], name="debug", level=logging_level)
    else:
        logger = fileio.logger_utils.initialize_logger(filename=parameters["loggername"], name="default", level=logging_level, disable_output=True)

    logger_by_rank = fileio.logger_utils.initialize_logger(filename=parameters["loggername"], name="by-rank", level=logging_level)

    if logging_level <= logging.DEBUG:
        debug_logger = fileio.logger_utils.initialize_logger(filename=parameters["loggername"], name="by-rank-debug", level=logging_level)

    parameters = fileio.set_default_parameters(parameters)

    globals()["parameters"] = parameters

    return parameters


# Used for `from StructOpt import *`
__all__ = ["Optimizer", "parameters"]
