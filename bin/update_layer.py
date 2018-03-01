
""" update layers in place """

# Import the PyQt and the QGIS libraries
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.utils import iface

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
    for k, v in myargs.iteritems():
        if re.match( k, 'master' ) :
            master_n = v
        elif re.match(k, 'update'):
            update_n = v
        elif re.match(k, 'match'):
            match_on = v
        elif re.match(k, 'help'):
            print "repository = ~/GPS-Data, newdir= <currentdate>, upload = False, layer = wp_master"
            exit_now = True
        else:
            print "I don't recognise option '" + k + "'"
            exit_now = True
    if exit_now:
        return

    print 'master = ', master_n, 'update = ', update_n
    master = find_layer(master_n)
    if not master :
        print "Cannot find layer '%s'", master_n
        return

    update = find_layer(update_n)
    if update:
        print "update:", update.name()
    else:
        print "no layer '%s'", update_n
        return

    editing = False
    update_features = {}  # indexed by feature attribute name
    for f in update.getFeatures():
        print f.attribute(match_on)
        update_features[f.attribute(match_on)] = f
#        print master.getFeatures( QgsFeatureRequest().setFilterExpression (
    # u'"{0}" = {1}'.format(match_on, f.attribute(match_on) )))

    print [field.name() for field in master.pendingFields() ]
    for m in master.getFeatures():
        n = m.attribute(match_on)
        if update_features.get(n, 'none') != 'none' :
            u = update_features[n]
            old = m.geometry().asPoint()
            new = u.geometry().asPoint()
            print n, old.x(), old.y()
            print n, new.x(), new.y()
            #if not m.geometry().equals( u.geometry()) :
            if not editing :
                editing = True
                master.startEditing()
            print 'updating', n
            print 'time', time.strftime("%Y-%m-%d %H:%M:%S")
            m['updated'] = time.strftime("%Y-%m-%d %H:%M:%S")
            print master.dataProvider().changeGeometryValues({ m.id() : u.geometry() })
            master.updateFeature(m)
            master.commitChanges()
            new = m.geometry().asPoint()
            print new.x(), new.y()
    #Call commit to save the changes

