import pytz

"""
This module contains a number of variables that readgssi needs to perform physics calculations and interpret files from DZT files.
"""


TZ = pytz.timezone('UTC')

# some physical constants for Maxwell's equation for speed of light in a dielectric medium
C = 299792458                   # speed of light in a vacuum
Eps_0 = 8.8541878 * 10**(-12)   # epsilon naught (vacuum permittivity)
Mu_0 = 1.257 * 10**(-6)         # mu naught (vacuum permeability)