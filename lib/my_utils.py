
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



def find_layer( layer_name ):
    layers = QgsMapLayerRegistry.instance().mapLayers()
    l = False
    for name, layer in layers.iteritems():
        if layer_name == layer.name(): # re.match(layer_name, layer.name()):
            l = layer
    return l


def wp_eq(wp1, wp2):
    return (wp1.latitude == wp2.latitude and wp1.longitude == wp2.longitude)

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

def get_wp_type( name ):

    if name[0] in wp_type_d:
        return wp_type_d[name[0]]
    return 'misc'


classes = {
    'B': {
        'H': 'Hihi',
        'T': 'saddleback',
        'K': 'Kakariki',
        'R': 'rifleman'
    }
}

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

def set_attrb(fet, name, val, defaults, default = None ):  #
    if not name in defaults:
        return
    v = val
    if not val :
        if not default:
            v = defaults[name]
        else:
            v = default
    if v :
        fet.setAttribute(name, v)

def canonicalise_name( name ):
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

def add_wp_layer( layer_name, model, gpx_points, defaults):
    # create layer

    # source crs
    crsSrc = QgsCoordinateReferenceSystem(4326)
    crsDest = model.crs()
    tr = QgsCoordinateTransform(crsSrc, crsDest)

    vl = QgsVectorLayer("Point?crs="+crsDest.authid(), layer_name, "memory")
    pr = vl.dataProvider()  # need to create data provider

    fields = model.pendingFields()

    if fields[0].name() == 'gid':
        fields.remove(0)  # let postgis set the gid
    pr.addAttributes(fields)
    vl.updateFields()  # tell the vector layer to fetch changes from the provider

    vl.updateFields()  # tell the vector layer to fetch changes from the provider
    fields = vl.pendingFields()

    # build a hash if the filed names with default values if given
    template = {}
    for f in fields:
        name = f.name()
        template[name] = None
        if name in defaults:
            template[name] = defaults[name]

    # now add the points
    features = []
    for wp in gpx_points:
        n = wp.name
        [wp_t, cl, cn] = canonicalise_name(wp.name)

        time = wp.time
        if wp.time:
            time =  wp.time.strftime("%Y-%m-%d %T")

        fet = QgsFeature()
        fet.setFields(fields, True)

        point = tr.transform( QgsPoint( wp.longitude, wp.latitude) )
        fet.setGeometry(QgsGeometry(QgsPointV2(QgsWKBTypes.PointZ, point.x(), point.y(), 0.0)))

        set_attrb(fet, 'name', cn, template )
        set_attrb(fet, 'rw_id', wp.comment, template, n)
        set_attrb(fet, 'created', time, template )
        set_attrb(fet, 'type', wp_type_d[wp_t], template )
        set_attrb(fet, 'classification', cl, template)
        set_attrb(fet, 'updated', time, template)
        set_attrb(fet, 'source', None, template )
        features.append(fet)

    pr.addFeatures(features)
    vl.updateExtents()
    QgsMapLayerRegistry.instance().addMapLayer(vl)

def export_gpx_files( layer_name, rw_id ):

    #this stuff should be in a configuration file

    nestbox = {
        'hihi': 'Navaid, Black',
        'saddleback': 'Navaid, Orange',
        'kakariki': 'Circle, Red',
        'rifleman': 'Circle, Green',
        'default': 'Navaid, blue',
        'files': True   # separate files please!
    }
    nestbox_default = 'Navaid, White',


    weeds = {
        'mp': 'Block, Blue',
        'sp': 'Flag, Blue',
        'mm': 'Diamond, Blue',
        'pw': 'Square, Blue',
        'default': 'Navaid, Blue',
        'files': False
    }
    weeds_default = 'Pin, Blue'
    print type(weeds)
    test = 1
    markers = {  # by type
        'weed': weeds,
        'nb': nestbox,
        'sign': 'Pin, Green',
        'track': 'Flag, Red',
        'files': False
    }

    # build a list of file from the config above

    files = []
    gpx_out = {}

    for k, v in markers.iteritems():
        if type(v) is dict  and v['files']:
            for  kk, vv in v.iteritems():
                if kk != 'files' and kk != 'default' :
                    files.append(kk)
        elif k != 'files' :
            files.append( k )

    #print files

    for f in files:
        gpx_out[f] = gpxpy.gpx.GPX()

    # set up CRS transform

    layer = find_layer(layer_name)
    crsDst = QgsCoordinateReferenceSystem(4326)
    crsSrc = layer.crs()
    tr = QgsCoordinateTransform(crsSrc, crsDst)


    # iterate over features in layer

    for feature in layer.getFeatures():
        point = feature.geometry()
        point.transform(tr)
        point = point.asPoint()

        ftype = feature['type']
        if ftype not in markers:
            continue

        m = markers[ftype]
        if type( m ) is dict :  # there is a nested list
            ind_files = m['files']
            if feature['classification'] :
                c = feature['classification'].lower()
                if c in m:
                    m = m[c]
                else:
                    m = m['default']
            else:
                continue
            if ind_files: # true if we want individual files
                ftype = c
        #print feature['type'], ftype, m
        if ftype not in gpx_out:
            continue

        name = feature['name']
        if rw_id and feature['rw_id'] !='' :
            name = feature['rw_id']
        cmt = ''
        if feature['description']:
            cmt = feature['description']
        # create gpx waypoint

        wp = gpxpy.gpx.GPXWaypoint(latitude=point.y(), longitude=point.x(),
                                   name=name, comment=cmt, symbol=m)
        #print name
        gpx_out[ftype].waypoints.append( wp )
        gpx_out[ftype].to_xml()

    export_dir = 'current/gpx_export'
    ensure_dir( export_dir )

    for file in files:
        #print file
        #print gpx_out[file].waypoints
        with open( export_dir + '/' + file + '.gpx', 'w') as gpx_file:
            gpx_file.write( gpx_out[file].to_xml())


def find_gps_devices( gps_mount, device_list ):

    if os.path.exists(device_list):
        with open(device_list) as json_data:
            d = json.load(json_data)
            devices = d['devices']

    device_dirs = {}

    for vol in os.listdir(gps_mount):
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
                    device_dirs[devices[id]] = garmin_dir
                else:
                    print "Can not find device " + id + " in devices file"
                    os.exit
    return device_dirs

def md5_file( name ):
    md5 = hashlib.md5()
    file = open(name, 'rb')
    while True:
        data = file.read(8192)
        if not data:
            break
        md5.update(data)

    file.close()
    return md5

def import_gpx_files( new_dir, gps_mount, upload ):

    new_files = './current/new_files'
    # keep_data_for = ' 6 months'
    devices = {}


    archive = {}

    # copy all the files from the latest directory to new_dir and compute md5 for all gpx files

    if upload:
        ensure_dir(new_dir)
        os.remove('./current')
        os.symlink(new_dir, './current')
        ensure_dir(new_files)
        for f in os.listdir("latest"):
            if os.path.isdir("latest/" + f):
                continue
            digest = None

            #  next unless f.match(/-(Track|Wayp).+\.gpx$/)
            nf = new_dir + '/' + 'f'
            if os.path.exists(nf):
                digest = md5_file('latest/' + 'f')
                if digest == hashlib.md5(nf):  # they are the same
                    continue
            latest = 'latest/' + f
            sysx(['cp', '-p', latest, new_dir + '/' + f])
            archive[f] = {'mtime': os.path.getmtime(latest)}
            if not 'digest' in archive[f]:
                archive[f]['digest'] = md5_file(latest)

        for device, gps_dir in find_gps_devices(gps_mount, 'devices.json' ).iteritems():

            # for each gpx file on the device  copy new or changed files to :new_files
            #   all have already been copied to
#            os.system( 'pwd' )
            p = re.compile(r'(Track|Wayp).+\.gpx$')
            for f in os.listdir(gps_dir + '/GPX'):
                if p.match(f):
                    fp = gps_dir + '/GPX/' + f
                    ff = device + '-' + f
                    if ff not in archive or (archive[ff]['digest'].digest() != md5_file(fp).digest() ) :
                        sysx(['cp', '-p', fp, new_dir + '/' + ff])  # Copy it to new archive
                        os.symlink(  '../' + ff, new_files + '/' + ff )
#                        sysx(['cp', '-p', fp, new_files + '/' + ff])  # Copy it to :new_files for further processing

    # At this point we should have an archive copy of the GPX directory in new_dir
    # and a copy of all new/chagned files in :new_files
    # instantiate gpx object to hold new and changed objects

    changed = gpxpy.gpx.GPX()
    new = gpxpy.gpx.GPX()

    for f in os.listdir(new_files):

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
            with open(new_files + '/' + f, 'r')  as gpx_file:
                try:
                    gpx = gpxpy.parse(gpx_file)
                except:
                    print "error parsing " + new_files+ '/' + f
                    continue

                for wp in gpx.waypoints:
                    # if wp.extensions:
                    # print 'ext:', wp.extensions #['wptx1:WaypointExtension']
                    # wp.cmt = wp.extensions['Samples']
                    if original:
                        if wp.name not in original:
                            new.waypoints.append(wp)
                        elif not wp_eq(original[wp.name], wp):
                            changed.waypoints.append(wp)
                    else:
                        new.waypoints.append(wp)

    if new.waypoints:
        with open(new_files +'/new.gpx', 'w') as output:
            output.write(new.to_xml())

    if changed.waypoints:
        with open(new_files + '/changed.gpx', 'w') as output:
            output.write(changed.to_xml())
    return [new.waypoints, changed.waypoints]
