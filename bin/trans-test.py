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




def run_script(iface, **myargs): # repository, new_dir, mount, upload ):



    trans = QgsCoordinateTransform( QgsCoordinateReferenceSystem('EPSG:4326'),
                                    QgsCoordinateReferenceSystem('EPSG:2193:'),
                                    QgsProject.instance() )


    new_point = QgsPoint(0, 0)

    new_point.transform(trans)
