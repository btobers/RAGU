import struct
import math
import os,sys
import numpy as np
from datetime import datetime
from itertools import takewhile
from geopy.distance import geodesic
from constants import *
import pandas as pd
import pynmea2

"""
this module contains functions parsed from https://github.com/iannesbitt/readgssi to read gssi dzt files and associated dzg files for use in NOSEpick
much of the header data which is not necessary for NOSEpick use has been removed

the main function, readdzt(), returns header information in dictionary format
and the radar profile in a numpy array.

Brandon S. Tober
09JUL2020
"""

def readtime(bytes):
    """
    Function to read dates from the :code:`rfDateByte` binary objects in DZT headers. 

    DZT :code:`rfDateByte` objects are 32 bits of binary (01001010111110011010011100101111), structured as little endian u5u6u5u5u4u7 where all numbers are base 2 unsigned int (uX) composed of X number of bits. It's an unnecessarily high level of compression for a single date object in a filetype that often contains tens or hundreds of megabytes of array information anyway.

    So this function reads (seconds/2, min, hr, day, month, year-1980) then does seconds*2 and year+1980 and returns a datetime object.

    For more information on :code:`rfDateByte`, see page 55 of `GSSI's SIR 3000 manual <https://support.geophysical.com/gssiSupport/Products/Documents/Control%20Unit%20Manuals/GSSI%20-%20SIR-3000%20Operation%20Manual.pdf>`_.

    :param bytes bytes: The :code:`rfDateByte` to be decoded
    :rtype: :py:class:`datetime.datetime`
    """
    dtbits = ''
    rfDateByte = (b for b in bytes)
    for byte in rfDateByte:                    # assemble the binary string
        for i in range(8):
            dtbits += str((byte >> i) & 1)
    dtbits = dtbits[::-1]               # flip the string
    sec2 = int(dtbits[27:32], 2) * 2    # seconds are stored as seconds/2 because there's only 5 bytes to work with
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

    '''
    currently unused but potentially useful lines:
    # headerstruct = '<5h 5f h 4s 4s 7h 3I d I 3c x 3h d 2x 2c s s 14s s s 12s h 816s 76s' # the structure of the bytewise header and "gps data" as I understand it - 1024 bytes
    # readsize = (2,2,2,2,2,4,4,4,4,4,2,4,4,4,2,2,2,2,2,4,4,4,8,4,3,1,2,2,2,8,1,1,14,1,1,12,2) # the variable size of bytes in the header (most of the time) - 128 bytes
    # print('total header structure size: '+str(calcsize(headerstruct)))
    # packed_size = 0
    # for i in range(len(readsize)): packed_size = packed_size+readsize[i]
    # print('fixed header size: '+str(packed_size)+'\\n')
    '''
    infile_dzx = fpath.replace(".DZT",".DTX")

    infile = open(fpath, 'rb')
    header = {}

    # begin read
    header['rh_tag'] = struct.unpack('<h', infile.read(2))[0] # 0x00ff if header, 0xfnff if old file format
    header['rh_data'] = struct.unpack('<h', infile.read(2))[0] # offset to data from beginning of file
    header['rh_nsamp'] = struct.unpack('<h', infile.read(2))[0] # samples per scan
    header['rh_bits'] = struct.unpack('<h', infile.read(2))[0] # bits per data word
    header['rh_zero'] = struct.unpack('<h', infile.read(2))[0] # if sir-30 or utilityscan df, then repeats per sample; otherwise 0x80 for 8bit and 0x8000 for 16bit
    header['rhf_sps'] = struct.unpack('<f', infile.read(4))[0] # scans per second
    header['rhf_spm'] = struct.unpack('<f', infile.read(4))[0] # scans per meter
    header['dzt_spm'] = header['rhf_spm']
    header['rhf_mpm'] = struct.unpack('<f', infile.read(4))[0] # meters per mark
    header['rhf_position'] = struct.unpack('<f', infile.read(4))[0] # position (ns)
    header['rhf_range'] = struct.unpack('<f', infile.read(4))[0] # range (ns)
    header['rh_npass'] = struct.unpack('<h', infile.read(2))[0] # number of passes for 2-D files
    # bytes 32-36 and 36-40: creation and modification date and time in bits
    # structured as little endian u5u6u5u5u4u7
    infile.seek(32)
    try:
        header['rhb_cdt'] = readtime(infile.read(4))
    except:
        header['rhb_cdt'] = datetime(1980, 1, 1)
    try:
        header['rhb_mdt'] = readtime(infile.read(4))
    except:
        header['rhb_mdt'] = datetime(1980, 1, 1)

    header['rh_rgain'] = struct.unpack('<h', infile.read(2))[0] # offset to range gain function
    header['rh_nrgain'] = struct.unpack('<h', infile.read(2))[0] # size of range gain function
    header['rh_text'] = struct.unpack('<h', infile.read(2))[0] # offset to text
    header['rh_ntext'] = struct.unpack('<h', infile.read(2))[0] # size of text
    header['rh_proc'] = struct.unpack('<h', infile.read(2))[0] # offset to processing history
    header['rh_nproc'] = struct.unpack('<h', infile.read(2))[0] # size of processing history
    header['rh_nchan'] = struct.unpack('<h', infile.read(2))[0] # number of channels
    header['rhf_epsr'] = struct.unpack('<f', infile.read(4))[0] # epsr (sometimes referred to as "dielectric permittivity")
    header['dzt_epsr'] = header['rhf_epsr']
    header['rhf_top'] = struct.unpack('<f', infile.read(4))[0] # position in meters (useless?)
    header['dzt_depth'] = struct.unpack('<f', infile.read(4))[0] # range in meters based on DZT rhf_epsr
    header['rhf_depth'] = header['dzt_depth'] * (math.sqrt(header['dzt_epsr']) / math.sqrt(header['rhf_epsr'])) # range based on user epsr

    header['cr'] = 1 / math.sqrt(Mu_0 * Eps_0 * header['rhf_epsr'])
    header['cr_true'] = 1 / math.sqrt(Mu_0 * Eps_0 * header['dzt_epsr'])
    header['dt'] = (header['dzt_depth'] * 2) / (header['rh_nsamp'] * header['cr_true'])

    # skip ahead to data
    if header['rh_data'] < 1024: # whether or not the header is normal or big-->determines offset to data array
        infile.seek(1024 * header['rh_data'])
    else:
        infile.seek(1024 * header['rh_nchan'])

    if header['rh_bits'] == 8:
        dtype = np.uint8 # 8-bit unsigned
    elif header['rh_bits'] == 16:
        dtype = np.uint16 # 16-bit unsigned
    else:
        dtype = np.int32 # 32-bit signed
            
    # read in and transpose data - as float 
    data = np.fromfile(infile, dtype).reshape(-1,(header['rh_nsamp']*header['rh_nchan'])).T.astype(np.float) # offset=start_offset,

    # replace missing data samples with nan
    data[data == 0] = np.nan

    # close data file
    infile.close()

    # if os.path.isfile(infile_gps):
    #     try:
    #         gps = readdzg(infile_gps, 'dzg', header)
    #     except IOError as e0:
    #         print('WARNING: cannot read DZG file')
    #         try:
    #             infile_gps = os.path.splitext(infile_gps)[0] + ".csv"
    #             gps = readdzg(infile_gps, 'csv', header)
    #         except Exception as e1:
    #             try:
    #                 infile_gps = os.path.splitext(infile_gps)[0] + ".CSV"
    #                 gps = readdzg(infile_gps, 'csv', header)
    #             except Exception as e2:
    #                 print('ERROR reading GPS. distance normalization will not be possible.')
    #                 print('   details: %s' % e0)
    #                 print('            %s' % e1)
    #                 print('            %s' % e2)
    #                 gps = []
    # else:
    #     print('WARNING: no DZG file found for GPS input')

    # header['marks'] = []
    # header['picks'] = {}

    # if os.path.isfile(infile_dzx):
    #     header['marks'] = get_user_marks(infile_dzx, verbose=verbose)
    #     header['picks'] = get_picks(infile_dzx, verbose=verbose)
    # else:
    #     print('WARNING: could not find DZX file to read metadata. Trying to read array for marks...')

    # tnums = np.ndarray.tolist(data[0])  # the first row of the array is trace number
    # usr_marks = np.ndarray.tolist(data[1])  # when the system type is SIR3000, the second row should be user marks (otherwise these are in the DZX, see note below)
    # i = 0
    # for m in usr_marks:
    #     if m > 0:
    #         print(m)
    #         header['marks'].append(i)
    #     i += 1
    # print('DZT marks read successfully. marks: %s' % len(header['marks']))
    # print('                            traces: %s' % header['marks'])

    return header, data.astype(np.float)

def readdzg(fpath, frmt, header):
    """
    A parser to extract gps data from DZG file format. DZG contains raw NMEA sentences, which should include at least RMC and GGA.

    NMEA RMC sentence string format:
    :py:data:`$xxRMC,UTC hhmmss,status,lat DDmm.sss,lon DDDmm.sss,SOG,COG,date ddmmyy,checksum \*xx`

    NMEA GGA sentence string format:
    :py:data:`$xxGGA,UTC hhmmss.s,lat DDmm.sss,lon DDDmm.sss,fix qual,numsats,hdop,mamsl,wgs84 geoid ht,fix age,dgps sta.,checksum \*xx`
    
    Shared message variables between GGA and RMC: timestamp, latitude, and longitude

    RMC contains a datestamp which makes it preferable, but this parser will read either.

    :param str fi: File containing gps information
    :param str frmt: GPS information format ('dzg' = DZG file containing gps sentence strings (see below); 'csv' = comma separated file with: lat,lon,elev,time)
    :param dict header: File header produced by :py:func:`readgssi.dzt.readdzt`
    :param bool verbose: Verbose, defaults to False
    :rtype: GPS data (pandas.DataFrame)

        The dataframe contains the following fields:
        * datetimeutc (:py:class:`datetime.datetime`)
        * trace (:py:class:`int` trace number)
        * longitude (:py:class:`float`)
        * latitude (:py:class:`float`)
        * altitude (:py:class:`float`)
        * velocity (:py:class:`float`)
        * sec_elapsed (:py:class:`float`)
        * meters (:py:class:`float` meters traveled)

    """

    # initialize data arrays
    trace_num = np.array(())
    lon = np.array(())
    lat = np.array(())
    elev = np.array(())

    if header['rhf_spm'] == 0:
        spu = header['rhf_sps']
    else:
        spu = header['rhf_spm']

    trace = 0 # the elapsed number of traces iterated through
    tracenum = 0 # the sequential increase in trace number
    rownp = 0 # array row number
    rowrmc = 0 # rmc record iterated through (gps file)
    rowgga = 0 # gga record
    sec_elapsed = 0 # number of seconds since the start of the line
    m = 0 # meters traveled over entire line
    m0, m1 = 0, 0 # meters traveled as of last, current loop
    u = 0 # velocity
    u0 = 0 # velocity on last loop
    timestamp = False
    prevtime = False
    init_time = False
    td = False
    prevtrace = False
    rmc, gga = False, False
    rmcwarn = True
    lathem = 'north'
    lonhem = 'east'
    x0, x1, y0, y1 = False, False, False, False # coordinates
    z0, z1 = 0, 0
    x2, y2, z2, sec2 = 0, 0, 0, 0
    with open(fpath, 'r') as gf:
        if frmt == 'dzg': # if we're working with DZG format
            for ln in gf: # loop through the first few sentences, check for RMC
                if 'RMC' in ln: # check to see if RMC sentence (should occur before GGA)
                    rmc = True
                    if rowrmc == 0:
                        msg = pynmea2.parse(ln.rstrip()) # convert gps sentence to pynmea2 named tuple
                        ts0 = TZ.localize(datetime.combine(msg.datestamp, msg.timestamp)) # row 0's timestamp (not ideal)
                    if rowrmc == 1:
                        msg = pynmea2.parse(ln.rstrip())
                        ts1 = TZ.localize(datetime.combine(msg.datestamp, msg.timestamp)) # row 1's timestamp (not ideal)
                        td = ts1 - ts0 # timedelta = datetime1 - datetime0
                    rowrmc += 1
                if 'GGA' in ln:
                    gga = True
                    if rowgga == 0:
                        msg = pynmea2.parse(ln.rstrip()) # convert gps sentence to pynmea2 named tuple
                        ts0 = TZ.localize(datetime.combine(datetime(1980, 1, 1), msg.timestamp)) # row 0's timestamp (not ideal)
                    if rowgga == 1:
                        msg = pynmea2.parse(ln.rstrip())
                        ts1 = TZ.localize(datetime.combine(datetime(1980, 1, 1), msg.timestamp)) # row 1's timestamp (not ideal)
                        td = ts1 - ts0 # timedelta = datetime1 - datetime0
                    rowgga += 1
            gpssps = 1 / td.total_seconds() # GPS samples per second
            # if (rmcwarn) and (rowrmc == 0):
            #     print('WARNING: no RMC sentences found in GPS records. this could become an issue if your file goes through 00:00:00.')
            #     print("         if you get a time jump error please open a github issue at https://github.com/iannesbitt/readgssi/issues")
            #     print("         and attach the verbose output of this script plus a zip of the DZT and DZG files you're working with.")
            #     rmcwarn = False
            # if (rmc and gga) and (rowrmc != rowgga):
            #     if verbose:
            #         print('WARNING: GGA and RMC sentences are not recorded at the same rate! This could cause unforseen problems!')
            #         print('    rmc: %i records' % rowrmc)
            #         print('    gga: %i records' % rowgga)
            # if verbose:
            #     ss0, ss1, ss2 = '', '', ''
            #     if gga:
            #         ss0 = 'GGA'
            #     if rmc:
            #         ss2 = 'RMC'
            #     if gga and rmc:
            #         ss1 = ' and '
            #     print('found %i %s%s%s GPS epochs at rate of ~%.2f Hz' % (rowrmc, ss0, ss1, ss2, gpssps))
            #     print('reading gps locations to data frame...')

            gf.seek(0) # back to beginning of file
            rowgga, rowrmc = 0, 0
            for ln in gf: # loop over file line by line
                if '$GSSIS' in ln:
                    # if it's a GSSI sentence, grab the scan/trace number
                    trace = int(ln.split(',')[1])

                # if (rmc and gga) and ('GGA' in ln):
                #     # RMC doesn't use altitude so if it exists we include it from a neighboring GGA
                #     z1 = pynmea2.parse(ln.rstrip()).altitude
                #     if rowrmc != rowgga:
                #         # this takes care of the case where RMC lines occur above GGA
                #         z0 = array['altitude'].iat[rowgga]
                #         array['altitude'].iat[rowgga] = z1
                #     rowgga += 1

                if rmc == True: # if there is RMC, we can use the full datestamp but there is no altitude
                    if 'RMC' in ln:
                        msg = pynmea2.parse(ln.rstrip())
                        timestamp = TZ.localize(datetime.combine(msg.datestamp, msg.timestamp)) # set t1 for this loop
                        u = msg.spd_over_grnd * 0.514444444 # convert from knots to m/s

                        sec1 = timestamp.timestamp()
                        x1, y1 = float(msg.longitude), float(msg.latitude)
                        if msg.lon_dir in 'W':
                            lonhem = 'west'
                        if msg.lat_dir in 'S':
                            lathem = 'south'
                        if rowrmc != 0:
                            elapsedelta = timestamp - prevtime # t1 - t0 in timedelta format
                            elapsed = float((timestamp-init_time).total_seconds()) # seconds elapsed
                            m += u * elapsedelta.total_seconds()
                        else:
                            u = 0
                            m = 0
                            elapsed = 0
                            # if verbose:
                            #     print('record starts in %s and %s hemispheres' % (lonhem, lathem))
                        x0, y0, z0, sec0, m0 = x1, y1, z1, sec1, m # set xyzs0 for next loop
                        prevtime = timestamp # set t0 for next loop
                        if rowrmc == 0:
                            init_time = timestamp
                        prevtrace = trace

                        trace_num=np.append(trace_num,trace)
                        lon=np.append(lon,x1)
                        lat=np.append(lat,y1)
                        elev=np.append(elev,z1)

                        rowrmc += 1

                else: # if no RMC, we hope there is no UTC 00:00:00 in the file.........
                    if 'GGA' in ln:
                        msg = pynmea2.parse(ln.rstrip())
                        timestamp = TZ.localize(datetime.combine(header['rhb_cdt'], msg.timestamp)) # set t1 for this loop

                        sec1 = timestamp.timestamp()
                        x1, y1 = float(msg.longitude), float(msg.latitude)
                        try:
                            z1 = float(msg.altitude)
                        except AttributeError:
                            z1 = 0
                        if msg.lon_dir in 'W':
                            lonhem = 'west'
                        if msg.lat_dir in 'S':
                            lathem = 'south'
                        # if rowgga != 0:
                        #     m += geodesic((y1, x1, z1), (y0, x0, z0)).meters
                        #     if rmc == False:
                        #         u = float((m - m0) / (sec1 - sec0))
                        #     elapsedelta = timestamp - prevtime # t1 - t0 in timedelta format
                        #     elapsed = float((timestamp-init_time).total_seconds()) # seconds elapsed
                        #     if elapsed > 3600.0:
                        #         print("WARNING: Time jumps by more than an hour in this GPS dataset and there are no RMC sentences to anchor the datestamp!")
                        #         print("         This dataset may cross over the UTC midnight dateline!\nprevious timestamp: %s\ncurrent timestamp:  %s" % (prevtime, timestamp))
                        #         print("         trace number:       %s" % trace)
                        # else:
                        #     u = 0
                        #     m = 0
                        #     elapsed = 0
                        x0, y0, z0, sec0, m0 = x1, y1, z1, sec1, m # set xyzs0 for next loop
                        prevtime = timestamp # set t0 for next loop
                        if rowgga == 0:
                            init_time = timestamp
                        prevtrace = trace

                        trace_num=np.append(trace_num,trace)
                        lon=np.append(lon,x1)
                        lat=np.append(lat,y1)
                        elev=np.append(elev,z1)
                        
                        rowgga += 1


        elif frmt == 'csv':
            with open(fi, 'r') as f:
                gps = np.fromfile(f)

    return {"trace":trace_num,"lon":lon,"lat":lat,"elev":elev}