""" update layers in place """

# Import the PyQt and the QGIS libraries
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from qgis.core import *
from qgis.utils import iface

import time
import re
import string
import sys, os, re

def run_script(iface):

    layers = QgsMapLayerRegistry.instance().mapLayers()

    master = update = None
    for name, layer in layers.iteritems():
        if 'wp_master' == layer.name():
            master = layer
        elif 'changed'  == layer.name():
            update = layer

    update_features = {}  # indexed by feature attribute name
    for f in update.getFeatures():
        update_features[f.attribute('name')] = f

    master.startEditing()
    for m in master.getFeatures():
        n = m.attribute('name')
        if update_features.get(n, 'none') != 'none':
            u = update_features[n]
            old = m.geometry().asPoint()
            new = u.geometry().asPoint()
            print( 'master', n, old.x(), old.y() )
            print( 'new', n, new.x(), new.y() )
            # if not m.geometry().equals( u.geometry()) :
            print(  'updating', n )
            print( 'time', time.strftime("%Y-%m-%d %H:%M:%S") )
            m['updated'] = time.strftime("%Y-%m-%d %H:%M:%S")
            master.dataProvider().changeGeometryValues({m.id(): u.geometry()})
            master.updateFeature(m)
            master.commitChanges()
            new = m.geometry().asPoint()
            print( 'nex x,y ', new.x(), new.y() )



