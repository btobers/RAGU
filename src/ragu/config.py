# create ragu config file
import configparser

def create_config(fpath):
    
    config = configparser.ConfigParser(allow_no_value=True, delimiters='=')
    config.add_section('param')
    config.set('param', '# str uid: user id')
    config.set('param', 'uid', '')
    config.set('param', '# str cmap: Matplotlib colormap to use (default = seismic)')
    config.set('param', 'cmap', '')

    config.add_section('path')
    config.set('path', '# str datPath: path to data files (optional)')
    config.set('path', 'datPath', '')
    config.set('path', '# str simPath: path to clutter simulations (optional)')
    config.set('path', 'simPath', '')
    config.set('path', '# str mapPath: path to basemap geotiff files (optional)')
    config.set('path', 'mapPath', '')
    config.set('path', '# str outPath: output path (optional)')
    config.set('path', 'outPath', '')

    config.add_section('nav')
    config.set('nav', '# str body: planetary body from which radar data was acquired (earth, moon, mars)')
    config.set('nav', 'body', 'earth')
    config.set('nav', '# str navcrs: crs string')
    config.set('nav', '# wgs84 projection string for earth: +proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs')
    config.set('nav', '# longlat projection string for mars: +proj=longlat +a=3396190 +b=3376200 +no_defs')
    config.set('nav', 'crs', 'proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs')

    config.add_section('output')
    config.set('output', '# float asep: antenna separation in meters (optional)')
    config.set('output', 'asep', '')
    config.set('output', '# float eps_r: relative permittivity (dielectric constant), required for plotting in depth and calculating layer thickness')
    config.set('output', 'eps_r', '3.15')
    config.set('output','# bool amp: export pick amplitudes')
    config.set('output','amp', 'True')
    config.set('output','# bool csv: export csv file of picks')
    config.set('output','csv', 'True')
    config.set('output','# bool gpkg: export geopackage of picks')
    config.set('output','gpkg', 'True')
    config.set('output','# bool fig: export radargram figure with any existing picks')
    config.set('output','fig', 'True')
    with open(fpath, 'w') as f:
        config.write(f)