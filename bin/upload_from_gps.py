""" upload and process gpx files from one or more Garmin GPSs """

from time import localtime, strftime
import sys, os, re
from datetime import datetime
from dateutil.parser import parse
#import pandas as pd
from os.path import expanduser, exists
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lib'))


from my_utils import  import_gpx_files, add_wp_layer, find_layer, get_device_config

def run_script(iface, **myargs): # repository, new_dir, mount, upload ):


    master = None

    date = strftime("%Y-%m-%d", localtime())
    now = strftime("%Y-%m-%d %H:%M:%S", localtime())

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

    defaults = {
        'created': now,
        'source': 'RJF',
        'updated': now
    }

    print( results )

    if results[0] : # new
        add_wp_layer('new', master, results[0], defaults )
    del defaults['created'] # only new items have a 'created' set
    if results[1] :
        add_wp_layer('changed', master,  results[1], defaults )
        #add_wp_layer('changed', {  'name': QVariant.String, 'time': QVariant.String } , results[1]) # just name and updated geometry
