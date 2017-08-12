
# Import the PyQt and the QGIS libraries
# Import the PyQt and the QGIS libraries
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *

import hashlib
import gpxpy
import gpxpy.gpx
import json
import re
import os, errno
import os.path
import subprocess

wp_type_d = {
    'R': 'rt',
    'B': 'nb',
    'S': 'sign',
    'T': 'track',
    'R': 'rt',
    'C': 'stream',
    'M': 'misc',
    'W': 'weed'
}
classes = {
    'B': {
        'H': 'Hihi',
        'T': 'saddleback',
        'K': 'Kakariki',
        'R': 'rifleman'
    }
}



def find_layer( layer_name ):
    layers = QgsMapLayerRegistry.instance().mapLayers()
    l = False
    for name, layer in layers.iteritems():
        if layer_name == layer.name(): # re.match(layer_name, layer.name()):
            l = layer
    return l

def cmp_wp(wp1, wp2):
    wp1.latitude == wp2.latitude and wp1.longitude == wp2.longitude

def get_wp_type( name ):

    if name[0] in wp_type_d:
        return wp_type_d[name[0]]
    return 'misc'


def wp_classes( type, name ):
    if type in classes and name[2] in classes[type]:
        return classes[type][name[2]]
    elif type == 'weed':
        return name[2:3]
    else:
        return None

def ensure_dir(file_path):
    try:
        os.makedirs(file_path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

def sysx ( cmd ):
    subprocess.check_output(cmd)

def set_attrb(fet, name, val, default = None):
    v = val
    if  not val and default:
        v = default
    if v != None:
        fet.setAttribute(name, v)

def canonicalise_name( name ):
#    print name
    # T C ID
    i = 1
    wp_type = name[0]
    classf = None
    c = ''
    if wp_type not in wp_type_d:
        m = re.match( r'([A-Z]{2})(\d{4].*)', name )
        if m:
            wp_type = 'W'
            classf = m.group(1)
            rest = m.group(2)
        else:
            wp_type = 'M'  # misc
    else:
        while i < len(name) and name[i] == ' ': # find the second non blank char
            i += 1
        if wp_type in classes:
            c = name[i]
            if name[i] in classes[wp_type]:
                classf = classes[wp_type][c]
                i += 1
            else:
                c = '_'
        elif wp_type == 'W':
            classf = name[i:i+2]
            i += 2
        elif wp_type == 'R' and name[1] == 'T':
            i = 2
    while i < len(name) and name[i] == ' ':  # find the next non blank char
        i += 1
    rest = name[i:]
    cname = wp_type
    if classf:
        cname += ' '+ c
    cname += ' ' + rest
    #print wp_type, classf, cname
    return [ wp_type, classf, cname ]

def add_wp_layer( name, model, gpx_points, defaults ):
    # create layer a layer the same as 'model' and load the gpx way_points into it

    # source crs
    crsSrc = QgsCoordinateReferenceSystem(4326)
    # target crs
    crsDest = model.crs()  # .authid()  # without () after originalLayer

    tr = QgsCoordinateTransform(crsSrc, crsDest)

    vl = QgsVectorLayer("PointZ?crs="+crsDest.authid(), name, "memory")
    pr = vl.dataProvider()  # need to create data provider

    #copy the field definitions from model
    template = {}

    for field in model.pendingFields():
        # print field.name(), field.isNumeric(), field.length(), field.precision()
        name = field.name()
        if name == 'gid':
            continue  # let postgis set the gid

        field_type = QVariant.String
        if field.isNumeric:
            if field.precision == 0:
                field_type = QVariant.Int
            else:
                field_type = QVariant.Double
        pr.addAttributes([QgsField(name, field_type )])
        template[name] = None
        if name in defaults:
            template[name] = defaults[name]

    vl.updateFields()  # tell the vector layer to fetch changes from the provider
    fields = vl.pendingFields()

    # now add the points

    features   = []
    for wp in gpx_points:
        n = wp.name
        [wp_t, cl, cn] = canonicalise_name(n)

        time = wp.time
        if wp.time:
            time =  wp.time.strftime("%Y-%m-%d %T")

        fet = QgsFeature()
        fet.setFields(fields, True)

        point = tr.transform( QgsPoint( wp.longitude, wp.latitude) )
        fet.setGeometry(QgsGeometry(QgsPointV2(QgsWKBTypes.PointZ, point.x(), point.y(), 0.0)))

        set_attrb(fet, 'name', cn )
        if 'rw_id' in template:
            set_attrb(fet, 'rw_id', wp.comment, n)
        if 'created' in template:
            default = None
            if 'created' in defaults:
                defefault = defaults['created']
            set_attrb(fet, 'created', time, default )
        #t = None
        if 'type' in template:
            set_attrb(fet, 'type', wp_type_d[wp_t] )
        if 'classification' in template:
            set_attrb(fet, 'classification', cl )
        if 'updated' in template:
            default = None
            if 'updated' in defaults:
                defefault = defaults['updated']
            set_attrb(fet, 'updated', time, default )
        if 'source' in template and 'source' in defaults:
            set_attrb(fet, 'source', defaults['source'] )
        features.append(fet)

    if pr.addFeatures(features):
        print 'addFeatures added ' + str(len(features)) + ' features'
    if not QgsMapLayerRegistry.instance().addMapLayer(vl):
        print 'addMapLayer failed'

def process_gpx_files( repository, new_dir, mount, upload ):

    current = './current'
    # keep_data_for = ' 6 months'
    devices = {}

    os.chdir(repository)

    if upload:
        ensure_dir(new_dir)
        ensure_dir(current)

    archive = {}

    # copy all the files from the latest directory to new_dir and compute md5 for all gpx files

    for f in os.listdir("latest"):
        if os.path.isdir("latest/" + f):
            continue
        digest = None

        #  next unless f.match(/-(Track|Wayp).+\.gpx$/)
        nf = new_dir + '/' + 'f'
        if os.path.exists(nf):
            digest = hashlib.md5('latest/' + 'f')
            if digest == hashlib.md5(nf):  # they are the same
                continue
        latest = 'latest/' + f
        if upload:
            sysx(['cp', '-p', latest, new_dir + '/' + f] )
        archive[f] = {'mtime': os.path.getmtime(latest)}
        if not 'digest' in archive[f]:
            archive[f]['digest'] = hashlib.md5(latest)

    if upload:
        dev_file = repository + '/devices.json'
        if os.path.exists(dev_file):
            with open('devices.json') as json_data:
                d = json.load(json_data)
                devices = d['devices']

        # find mounted gpses and loop over them
        for vol in os.listdir(mount):
            if not re.match('GARMIN', vol):
                continue
            device = ''

            # get the device ID form the device file

            id = ''
            garmin_dir = '/Volumes/' + vol + '/Garmin/'

            with open(garmin_dir + '/GarminDevice.xml', 'r') as f:
                for l in f:
                    m = re.search('<Id>(\d+)<\/Id>', l)
                    if m:
                        id = m.group(1)
                if id in devices:
                    device = devices[id]
                else:
                    print "Can not find device " + id + " in devices file"
                    os.exit

            # for each gpx file on the device  copy new or changed files to current
            #   all have already been copied to
            os.system( 'pwd' )
            p = re.compile(r'(Track|Wayp).+\.gpx$')
            for f in os.listdir(garmin_dir + '/GPX'):
                if p.match(f):
                    fp = garmin_dir + '/GPX/' + f
                    ff = device + '-' + f
                    if ff not in archive or (archive[ff]['digest'].digest() != hashlib.md5(garmin_dir + '/GPX/' + f).digest() ) :
                        sysx(['cp', '-p', fp,  current + '/' + ff])  # Copy it to current for further processing
                    sysx(['cp', '-p', fp, new_dir + '/' + ff ] )  # Copy it to new archive

    # At this point we should have an archive copy of the GPX directory in new_dir
    # and a copy of all new/chagned files in current
    # instantiate gpx object to hold new and changed objects

    changed = gpxpy.gpx.GPX()
    new = gpxpy.gpx.GPX()

    for f in os.listdir(current):

        if re.search(r'Waypoints.+\.gpx$', f):
            original = False
            if f in archive:  # existing file -- read it so we can figure out what changed
                original = {}
                with open('latest/' + f, 'r') as gpx_file:
                    try:
                        gpx = gpxpy.parse(gpx_file)
                    except:
                        print "error parsing latest/" + f
                        continue
                    for wp in gpx.waypoints:
                        original[wp.name] = wp
            with open('current/' + f, 'r')  as gpx_file:
                try:
                    gpx = gpxpy.parse(gpx_file)
                except:
                    print "error parsing current/" + f
                    continue
                for wp in gpx.waypoints:
                    # if wp.extensions:
                    # print 'ext:', wp.extensions #['wptx1:WaypointExtension']
                    # wp.cmt = wp.extensions['Samples']
                    if original:
                        if wp.name not in original:
                            new.waypoints.append(wp)
                        elif not cmp_wp( original[wp.name], wp ):
                            changed.waypoints.append(wp)
                    else:
                        new.waypoints.append(wp)

#    if master:


    if new.waypoints:
        with open('current/new.gpx', 'w') as output:
            output.write(new.to_xml())

    if changed.waypoints:
        with open('current/changed.gpx', 'w') as output:
            output.write(changed.to_xml())
    return [new.waypoints, changed.waypoints]


