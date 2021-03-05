### RAGU processing log ###
import sys
# change dir to RAGU code directory
sys.path.append('/mnt/c/Users/btobers/Documents/code/radar/RAGU/code')
from ingest import ingest

igst = ingest("/mnt/c/Users/btobers/Documents/data/radar/testdata/ARES/20140524-200130.h5")
rdata = igst.read("","+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs","earth")
rdata.lowpass(order=5, cf=1250000.0)
rdata.tpowGain(power=1.2)
