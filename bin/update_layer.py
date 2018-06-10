
""" update layers in place """

import time
import re
import string
import sys, os, re

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lib'))

from my_utils import find_layer

# from qgis.utils import iface


# from osgeo import ogr
# from osgeo import gdal

def run_script(iface, **myargs): # repository, new_dir, mount, upload ):

    master_n = 'wp_master'
    match_on = 'name'
    update_n = 'changed'

    exit_now = False
    for k, v in myargs.items():
        if re.match( k, 'master' ) :
            master_n = v
        elif re.match(k, 'update'):
            update_n = v
        elif re.match(k, 'match'):
            match_on = v
        elif re.match(k, 'help'):
            print( "repository = ~/GPS-Data, newdir= <currentdate>, upload = False, layer = wp_master" )
            exit_now = True
        else:
            print( "I don't recognise option '" + k + "'" )
            exit_now = True
    if exit_now:
        return

    editing = False
    update_features = {}
    master_features = {}

    print( 'master = ', master_n, 'update = ', update_n )
    master = find_layer(master_n)
    if not master :
        print( "Cannot find layer '%s'", master_n )
        return

    update = find_layer(update_n)
    if update:
        print( "update:", update.name() )
    else:
        print( "no layer '%s'", update_n )
        return

    for f in master.getFeatures():  # cache all featutes
        master_features[f.attribute(match_on)] = f

    for f in update.getFeatures():
        update_features[f.attribute(match_on)] = f

    geom_updates = {}
    for u in update.getFeatures():
        n = u.attribute(match_on)
        if n in master_features:
            m = master_features[n]
            u = update_features[n]
            if not editing :
                editing = True
                master.startEditing()
            geom_updates[m.id()]= u.geometry()
            master.updateFeature(m)
        else:
            print( "Warning: attribute", match_on, '(', n, ')',  'not found in layer', master_n )

    # do gemetry changes if any
    if len(geom_updates) > 0 :
        master.dataProvider().changeGeometryValues(geom_updates)

    # Call commit to save the changes
    master.commitChanges()


