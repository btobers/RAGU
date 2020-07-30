"""
this module contains functions parsed from https://github.com/iannesbitt/readgssi to read gssi dzt files and associated dzg files for use in NOSEpick
much of the header data which is not necessary for NOSEpick use has been removed
"""
### imports ###
from radar import radar
from nav import navparse
import struct
import math
import os,sys
import numpy as np
from datetime import datetime
from itertools import takewhile
from geopy.distance import geodesic
from tools.constants import *
import pandas as pd
import pynmea2

# method to read gssi dzt data
def read(fpath, navcrs, body):
    print("----------------------------------------")
    print("Loading: " + fpath.split("/")[-1])
    rdata = radar(fpath.split("/")[-1])
    # use readgssi readdzt.dzt reader (credit: https://github.com/iannesbitt/readgssi)
    header, rdata.dat = readdzt(fpath)#, gps=normalize, spm=spm, start_scan=start_scan, num_scans=num_scans, epsr=epsr, antfreq=antfreq, verbose=verbose)
    # convert gssi signed int amplitude to floating point for displaying
    rdata.proc_data = rdata.dat.astype(np.float)
    # ensure data file is not empty
    if not np.any(rdata.dat):
        print("gssi_read error: file contains no data")
        return

    rdata.snum = header["rh_nsamp"]
    rdata.tnum = rdata.dat.shape[1]
    rdata.dt = header["dt"]
    rdata.chan = header["rh_nchan"]
    rdata.clut = np.ones(rdata.dat.shape)                   # place holder for clutter data
    rdata.surf = np.repeat(np.nan, rdata.tnum)              # place holder for surface index

    # read in gps data if exists
    infile_gps = fpath.replace(".DZT",".DZG")
    if os.path.isfile(infile_gps):
        # create nav object to hold lon, lat, elev
        rdata.navdf = navparse.getnav_gssi(infile_gps, rdata.tnum, navcrs, body)

    else: 
        # if no gps data file, use nan arrays
        print("Warning: no associated nav data found")
        rdata.navdf["lon"] = np.nan
        rdata.navdf["lat"] = np.nan
        rdata.navdf["elev"] = np.nan
        rdata.navdf["dist"] = np.nan

    # for ground-based GPR, elev_gnd is the same as GPS recorded elev
    rdata.elev_gnd = rdata.navdf["elev"]
    
    return rdata


def readtime(bytes):
    """
    Function to read dates from the :code:`rfDateByte` binary objects in DZT headers. 

    DZT :code:`rfDateByte` objects are 32 bits of binary (01001010111110011010011100101111), structured as little endian u5u6u5u5u4u7 where all numbers are base 2 unsigned int (uX) composed of X number of bits. It"s an unnecessarily high level of compression for a single date object in a filetype that often contains tens or hundreds of megabytes of array information anyway.

    So this function reads (seconds/2, min, hr, day, month, year-1980) then does seconds*2 and year+1980 and returns a datetime object.

    For more information on :code:`rfDateByte`, see page 55 of `GSSI"s SIR 3000 manual <https://support.geophysical.com/gssiSupport/Products/Documents/Control%20Unit%20Manuals/GSSI%20-%20SIR-3000%20Operation%20Manual.pdf>`_.

    :param bytes bytes: The :code:`rfDateByte` to be decoded
    :rtype: :py:class:`datetime.datetime`
    """
    dtbits = ""
    rfDateByte = (b for b in bytes)
    for byte in rfDateByte:                    # assemble the binary string
        for i in range(8):
            dtbits += str((byte >> i) & 1)
    dtbits = dtbits[::-1]               # flip the string
    sec2 = int(dtbits[27:32], 2) * 2    # seconds are stored as seconds/2 because there"s only 5 bytes to work with
    mins = int(dtbits[21:27], 2)        # minutes
    hr = int(dtbits[16:21], 2)          # hours
    day = int(dtbits[11:16], 2)         # day
    mo = int(dtbits[7:11], 2)           # month
    yr = int(dtbits[0:7], 2) + 1980     # year, stored as 1980+(0:127)
    return datetime(yr, mo, day, hr, mins, sec2, 0, tzinfo=pytz.UTC)


def readdzt(fpath):
    """
    Function to unpack and return things the program needs from the file header, and the data itself.

    :param str infile: The DZT file location
    :param float spm: User value of samples per meter, if specified. Defaults to None.
    :param float epsr: User value of relative permittivity, if specified. Defaults to None.
    :param bool verbose: Verbose, defaults to False
    :rtype: header (:py:class:`dict`), radar array (:py:class:`numpy.ndarray`), gps (False or :py:class:`pandas.DataFrame`)
    """

    """
    currently unused but potentially useful lines:
    # headerstruct = "<5h 5f h 4s 4s 7h 3I d I 3c x 3h d 2x 2c s s 14s s s 12s h 816s 76s" # the structure of the bytewise header and "gps data" as I understand it - 1024 bytes
    # readsize = (2,2,2,2,2,4,4,4,4,4,2,4,4,4,2,2,2,2,2,4,4,4,8,4,3,1,2,2,2,8,1,1,14,1,1,12,2) # the variable size of bytes in the header (most of the time) - 128 bytes
    # print("total header structure size: "+str(calcsize(headerstruct)))
    # packed_size = 0
    # for i in range(len(readsize)): packed_size = packed_size+readsize[i]
    # print("fixed header size: "+str(packed_size)+"\\n")
    """
    infile_dzx = fpath.replace(".DZT",".DTX")

    infile = open(fpath, "rb")
    header = {}

    # begin read
    header["rh_tag"] = struct.unpack("<h", infile.read(2))[0] # 0x00ff if header, 0xfnff if old file format
    header["rh_data"] = struct.unpack("<h", infile.read(2))[0] # offset to data from beginning of file
    header["rh_nsamp"] = struct.unpack("<h", infile.read(2))[0] # samples per scan
    header["rh_bits"] = struct.unpack("<h", infile.read(2))[0] # bits per data word
    header["rh_zero"] = struct.unpack("<h", infile.read(2))[0] # if sir-30 or utilityscan df, then repeats per sample; otherwise 0x80 for 8bit and 0x8000 for 16bit
    header["rhf_sps"] = struct.unpack("<f", infile.read(4))[0] # scans per second
    header["rhf_spm"] = struct.unpack("<f", infile.read(4))[0] # scans per meter
    header["dzt_spm"] = header["rhf_spm"]
    header["rhf_mpm"] = struct.unpack("<f", infile.read(4))[0] # meters per mark
    header["rhf_position"] = struct.unpack("<f", infile.read(4))[0] # position (ns)
    header["rhf_range"] = struct.unpack("<f", infile.read(4))[0] # range (ns)
    header["rh_npass"] = struct.unpack("<h", infile.read(2))[0] # number of passes for 2-D files
    # bytes 32-36 and 36-40: creation and modification date and time in bits
    # structured as little endian u5u6u5u5u4u7
    infile.seek(32)
    try:
        header["rhb_cdt"] = readtime(infile.read(4))
    except:
        header["rhb_cdt"] = datetime(1980, 1, 1)
    try:
        header["rhb_mdt"] = readtime(infile.read(4))
    except:
        header["rhb_mdt"] = datetime(1980, 1, 1)

    header["rh_rgain"] = struct.unpack("<h", infile.read(2))[0] # offset to range gain function
    header["rh_nrgain"] = struct.unpack("<h", infile.read(2))[0] # size of range gain function
    header["rh_text"] = struct.unpack("<h", infile.read(2))[0] # offset to text
    header["rh_ntext"] = struct.unpack("<h", infile.read(2))[0] # size of text
    header["rh_proc"] = struct.unpack("<h", infile.read(2))[0] # offset to processing history
    header["rh_nproc"] = struct.unpack("<h", infile.read(2))[0] # size of processing history
    header["rh_nchan"] = struct.unpack("<h", infile.read(2))[0] # number of channels
    header["rhf_epsr"] = struct.unpack("<f", infile.read(4))[0] # epsr (sometimes referred to as "dielectric permittivity")
    header["dzt_epsr"] = header["rhf_epsr"]
    header["rhf_top"] = struct.unpack("<f", infile.read(4))[0] # position in meters (useless?)
    header["dzt_depth"] = struct.unpack("<f", infile.read(4))[0] # range in meters based on DZT rhf_epsr
    header["rhf_depth"] = header["dzt_depth"] * (math.sqrt(header["dzt_epsr"]) / math.sqrt(header["rhf_epsr"])) # range based on user epsr

    header["cr"] = 1 / math.sqrt(Mu_0 * Eps_0 * header["rhf_epsr"])
    header["cr_true"] = 1 / math.sqrt(Mu_0 * Eps_0 * header["dzt_epsr"])
    header["dt"] = (header["dzt_depth"] * 2) / (header["rh_nsamp"] * header["cr_true"])

    # skip ahead to data
    if header["rh_data"] < 1024: # whether or not the header is normal or big-->determines offset to data array
        infile.seek(1024 * header["rh_data"])
    else:
        infile.seek(1024 * header["rh_nchan"])

    if header["rh_bits"] == 8:
        dtype = np.uint8 # 8-bit unsigned
    elif header["rh_bits"] == 16:
        dtype = np.uint16 # 16-bit unsigned
    else:
        dtype = np.int32 # 32-bit signed
            
    # read in and transpose data - as float 
    amp = np.fromfile(infile, dtype).reshape(-1,(header["rh_nsamp"]*header["rh_nchan"])).T.astype(np.float) # offset=start_offset,

    # close data file
    infile.close()

    return header, amp


# def readdzg(fpath, frmt, header):
#     """
#     A parser to extract gps data from DZG file format. DZG contains raw NMEA sentences, which should include at least RMC and GGA.

#     NMEA RMC sentence string format:
#     :py:data:`$xxRMC,UTC hhmmss,status,lat DDmm.sss,lon DDDmm.sss,SOG,COG,date ddmmyy,checksum \*xx`

#     NMEA GGA sentence string format:
#     :py:data:`$xxGGA,UTC hhmmss.s,lat DDmm.sss,lon DDDmm.sss,fix qual,numsats,hdop,mamsl,wgs84 geoid ht,fix age,dgps sta.,checksum \*xx`
    
#     Shared message variables between GGA and RMC: timestamp, latitude, and longitude

#     RMC contains a datestamp which makes it preferable, but this parser will read either.

#     :param str fi: File containing gps information
#     :param str frmt: GPS information format ("dzg" = DZG file containing gps sentence strings (see below); "csv" = comma separated file with: lat,lon,elev,time)
#     :param dict header: File header produced by :py:func:`readgssi.dzt.readdzt`
#     :param bool verbose: Verbose, defaults to False
#     :rtype: GPS data (pandas.DataFrame)

#         The dataframe contains the following fields:
#         * datetimeutc (:py:class:`datetime.datetime`)
#         * trace (:py:class:`int` trace number)
#         * longitude (:py:class:`float`)
#         * latitude (:py:class:`float`)
#         * altitude (:py:class:`float`)
#         * velocity (:py:class:`float`)
#         * meters (:py:class:`float` meters traveled)

#     """

#     # initialize data arrays
#     trace_num = np.array(()).astype(np.int)
#     lon = np.array(()).astype(np.float64)
#     lat = np.array(()).astype(np.float64)
#     elev = np.array(()).astype(np.float64)

#     if header["rhf_spm"] == 0:
#         spu = header["rhf_sps"]
#     else:
#         spu = header["rhf_spm"]

#     trace = 0 # the elapsed number of traces iterated through
#     rowrmc = 0 # rmc record iterated through (gps file)
#     rowgga = 0 # gga record
#     timestamp = False
#     td = False
#     rmc, gga = False, False
#     x0, x1, y0, y1 = False, False, False, False # coordinates
#     z0, z1 = 0, 0
#     x2, y2, z2 = 0, 0, 0
#     with open(fpath, "r") as gf:
#         if frmt == "dzg": # if we"re working with DZG format
#             for ln in gf: # loop through the first few sentences, check for RMC
#                 if "RMC" in ln: # check to see if RMC sentence (should occur before GGA)
#                     rmc = True
#                     if rowrmc == 0:
#                         msg = pynmea2.parse(ln.rstrip()) # convert gps sentence to pynmea2 named tuple
#                         ts0 = TZ.localize(datetime.combine(msg.datestamp, msg.timestamp)) # row 0"s timestamp (not ideal)
#                     if rowrmc == 1:
#                         msg = pynmea2.parse(ln.rstrip())
#                         ts1 = TZ.localize(datetime.combine(msg.datestamp, msg.timestamp)) # row 1"s timestamp (not ideal)
#                         td = ts1 - ts0 # timedelta = datetime1 - datetime0
#                     rowrmc += 1
#                 if "GGA" in ln:
#                     gga = True
#                     if rowgga == 0:
#                         msg = pynmea2.parse(ln.rstrip()) # convert gps sentence to pynmea2 named tuple
#                         ts0 = TZ.localize(datetime.combine(datetime(1980, 1, 1), msg.timestamp)) # row 0"s timestamp (not ideal)
#                     if rowgga == 1:
#                         msg = pynmea2.parse(ln.rstrip())
#                         ts1 = TZ.localize(datetime.combine(datetime(1980, 1, 1), msg.timestamp)) # row 1"s timestamp (not ideal)
#                         td = ts1 - ts0 # timedelta = datetime1 - datetime0
#                     rowgga += 1
#             gpssps = 1 / td.total_seconds() # GPS samples per second

#             gf.seek(0) # back to beginning of file
#             for ln in gf: # loop over file line by line
#                 if "$GSSIS" in ln:
#                     # if it"s a GSSI sentence, grab the scan/trace number
#                     trace = int(ln.split(",")[1])

#                 if rmc == True: # if there is RMC, we can use the full datestamp but there is no altitude
#                     if "RMC" in ln:
#                         msg = pynmea2.parse(ln.rstrip())
#                         x1, y1 = float(msg.longitude), float(msg.latitude)
#                         x0, y0, z0 = x1, y1, z1 # set xyzs0 for next loop

#                         trace_num=np.append(trace_num,trace)
#                         lon=np.append(lon,x1)
#                         lat=np.append(lat,y1)
#                         elev=np.append(elev,z1)

#                 else: # if no RMC, we hope there is no UTC 00:00:00 in the file.........
#                     if "GGA" in ln:
#                         msg = pynmea2.parse(ln.rstrip())
#                         x1, y1 = float(msg.longitude), float(msg.latitude)
#                         try:
#                             z1 = float(msg.altitude)
#                         except AttributeError:
#                             z1 = 0
#                         x0, y0, z0 = x1, y1, z1 # set xyzs0 for next loop

#                         trace_num=np.append(trace_num,trace)
#                         lon=np.append(lon,x1)
#                         lat=np.append(lat,y1)
#                         elev=np.append(elev,z1)

#         elif frmt == "csv":
#             with open(fpath, "r") as f:
#                 gps = np.fromfile(f)

#     return {"trace":trace_num,"lon":lon,"lat":lat,"elev":elev}