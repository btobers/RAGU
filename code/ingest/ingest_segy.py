"""
Loading of SEGY files.
"""
### IMPORTS ###
import numpy as np
import sys
# from ..RadarData import RadarData
# from ..RadarFlags import RadarFlags

try:
    import segyio
    SEGY = True
except ImportError:
    SEGY = False


def read(gpath, *args, **kwargs):
    print("segy ingest still in development")
    sys.exit()
    """Load segy data.

    This is very generic for now, need to do work if there are particular
    types of segy files that need to be read. We cannot yet support a
    generic SEGY file, even if complies to some standard set.
    """
    if not SEGY:
        raise ImportError('Need segyio to load SGY files')
    segy_data = RadarData(None)
    segy_data.fn = fn_sgy
    f = segyio.open(fn_sgy, ignore_geometry=True)

    segy_data.data = segyio.tools.collect(f.trace).transpose()
    segy_data.snum = f.bin[segyio.BinField.Samples]
    segy_data.tnum = segy_data.data.shape[1]
    segy_data.dt = f.bin[segyio.BinField.Interval] * 1.0e-12
    segy_data.travel_time = np.arange(segy_data.snum) * segy_data.dt * 1.0e6
    segy_data.trace_num = np.arange(segy_data.data.shape[1]) + 1
    segy_data.flags = RadarFlags()
    # segy_data.travel_time = np.atleast_2d(np.arange(0,
    # segy_data.dt * segy_data.snum, segy_data.dt)).transpose()
    # + segy_data.dt

    # TODO  these next ones are filler
    # right now, they are selected so that they read in the delores data
    segy_data.trace_int = 1
    segy_data.chan = 1
    segy_data.trig = np.zeros((segy_data.tnum, ))
    segy_data.decday = np.zeros((segy_data.tnum, ))
    segy_data.x_coord = f.attributes(segyio.TraceField.CDP_X)[:] / 10.0
    segy_data.y_coord = f.attributes(segyio.TraceField.CDP_Y)[:] / 10.0
    segy_data.dist = np.hstack(([0],
                                np.cumsum(np.sqrt(
                                    np.diff(segy_data.x_coord)**2.0 + np.diff(
                                        segy_data.y_coord)**2.0)))) / 1000.
    segy_data.long = np.zeros((segy_data.tnum, ))
    segy_data.lat = np.zeros((segy_data.tnum, ))
    segy_data.elev = np.zeros((segy_data.tnum, ))
    segy_data.trig_level = np.zeros((segy_data.tnum, ))
    segy_data.pressure = np.zeros((segy_data.tnum, ))

    segy_data.check_attrs()
    return segy_data