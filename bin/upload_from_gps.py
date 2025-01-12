""" upload and process gpx files from one or more Garmin GPSs

    :parameters:

    wp_layer = 'wp_master'
    repository = expanduser('~') + "/Google Drive/Tiri/GPX repository/"
    upload = False
    newdir = <current date>  only relevant if upload is true
    layer = "wp_master"
    from = <date>   ignore gpx files older that this
"""

from time import localtime, strftime
import sys, os, re
from datetime import datetime
from dateutil.parser import parse

date = datetime.now().strftime("%Y-%m-%d")

from os.path import expanduser, exists
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lib'))
sys.path.append('/usr/local/lib/python3.7/site-packages')


from qgis_utils import  import_gpx_files, add_wp_layer, find_layer, get_device_config

def run_script(iface, **myargs): # repository, new_dir, mount, upload ):


    master = None


    repository = expanduser('~') + "/Google Drive/Tiri/GPX repository/"
    new_dir = date
    upload = False
    layer = 'wp_master'
    from_time = ft = None


    exit_now = False
    for k, v in myargs.items():
        if re.match( k, 'newdir' ) :
            new_dir = v
        elif re.match( k, 'repository' ):
            repository = v
        elif re.match( k, 'upload'):
            upload = v
        elif re.match(k, 'layer'):
            layer = v
        elif re.match(k, 'from'):
            ft = v
        elif re.match(k, 'help'):
            print ( "repository = ~/GPS-Data, newdir= <currentdate>, upload = False, layer = wp_master" )
            exit_now = True
        else:
            print ( "I don't recognise option '" + k + "'" )
            exit_now = True
    if exit_now:
        return

    print( 'upload ', upload, new_dir )

    os.chdir(repository)
    config = get_device_config('devices.json')
    defaults = config[1]
    devices = config[0]

    if ft:
        from_time= datetime.strptime(ft, '%Y-%m-%d')

    if os.path.exists('current'):
        if upload:
            os.remove('current')
        else:
            new_dir = 'current'

    master = find_layer( layer )

    results = import_gpx_files( new_dir, devices, upload, from_time )

