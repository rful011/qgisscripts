""" upload and process gpx files from one or more Garmin GPSs """

# Import the PyQt and the QGIS libraries

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *

from time import localtime, strftime
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lib'))

from my_utils import  process_gpx_files, add_wp_layer, find_layer


def run_script(iface, repository, new_dir, mount, upload ):


    master = None

    now = strftime("%Y-%m-%d %H:%M:%S", localtime())

    if repository == '' :
        repository = '/Users/rful011/GPS-Data'
    if new_dir == '' :
        new_dir= './' + now
    if mount == '':
        mount = '/Volumes'
    if upload == '':
        upload = False

    master = find_layer( 'wp_master')

    results = process_gpx_files(repository, new_dir, mount, upload )
    # print results

    defaults = {
        'created': now,
        'source': 'RJF',
        'updated': now
    }

    if results[0] : # new
        add_wp_layer('new', master, results[0], defaults )
    del defaults['created'] # only new items have a 'created' set
    if results[1] :
        add_wp_layer('changed', master,  results[1], defaults )
        #add_wp_layer('changed', {  'name': QVariant.String, 'time': QVariant.String } , results[1]) # just name and updated geometry