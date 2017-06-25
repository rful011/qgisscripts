
# Import the PyQt and the QGIS libraries
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.utils import iface

import time
import re
import string


# from qgis.utils import iface


# from osgeo import ogr
# from osgeo import gdal



def find_layer(layer_name):
    layers = QgsMapLayerRegistry.instance().mapLayers()
    l = False
    for name, layer in layers.iteritems():
        if layer_name == layer.name(): # re.match(layer_name, layer.name()):
            l = layer
    return l

def run_script(iface, m_l='wp-master', u_l='changed, waypoints', matchon = 'name'):

    if matchon == '':
        matchon = 'name'
        if m_l == '':
            m_l = 'wp_master'
    if u_l == '':
        u_l = 'changed, waypoints'


    print 'master = ', m_l, 'update = ', u_l
    master = find_layer(m_l)
    if not master :
        print "Cannot find layer " + "'" + m_l + "'"
        return

    update = find_layer(u_l)
    if update:
        print "update:", update.name()
    else:
        print "no layer "  + "'" + u_l + "'"
        return



    update_features = {}  # indexed by feature attribute name
    for f in update.getFeatures():
        print f
        update_features[f.attribute(matchon)] = f


    editing = False
    print [field.name() for field in master.pendingFields() ]
    for m in master.getFeatures():
        n = m.attribute(matchon)
        if update_features.get(n, 'none') != 'none' :
            u = update_features[n]
            print n, m.geometry(), u.geometry()
            #if not m.geometry().equals( u.geometry()) :
            if not editing :
                editing = True
                master.startEditing()
            print 'updating', n
            print 'time', time.strftime("%Y-%m-%d %H:%M:%S")
            m['updated'] = time.strftime("%Y-%m-%d %H:%M:%S")
            master.dataProvider().changeGeometryValues({ m.id() : u.geometry() })
            master.updateFeature(m)
    #Call commit to save the changes
    if editing :
        master.commitChanges()