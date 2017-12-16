
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
import math
import glob

def find_layer( layer_name ):
    layers = QgsMapLayerRegistry.instance().mapLayers()
    l = None
    for name, layer in layers.iteritems():
        if layer_name == layer.name(): # re.match(layer_name, layer.name()):
            l = layer
    return l

def wp_diff(wp1, wp2, tr = None, debug = None):
    if tr:
        geom = wp1
        geom.transform(tr)
        p = geom.asPoint()
        long = p.x()
        lat = p.y()
    else:
        long = wp1.longitude
        lat = wp1.latitude
    diff1 = lat - wp2.latitude
    diff2 = long - wp2.longitude
    if debug:
        print lat, wp2.latitude, long, wp2.longitude, math.sqrt(diff1**2 + diff2**2 )
    return  math.sqrt(diff1**2 + diff2**2 )


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
            i = 0
            if re.match(r'\d+$', name) :
                classf = 'tunnel'
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

def create_transform_to_WGS84( layer ):
    crsDst = QgsCoordinateReferenceSystem(4326)
    crsSrc = layer.crs()
    return QgsCoordinateTransform(crsSrc, crsDst)



def export_track_gpx_files( export_dir, layer_name ):

    #this stuff should be in a configuration file

    gpx_out = gpxpy.gpx.GPX()

    # set up CRS transform

    layer = find_layer(layer_name)
    if layer is None:
        print "Could not find layer '" + layer_name + "'"
        return False
    tr = create_transform_to_WGS84( layer )

    # iterate over features in layer

    for feature in layer.getFeatures():
        geom = feature.geometry()
        geom.convertToMultiType()
        geom.transform(tr)
        segments = geom.asMultiPolyline()

        name = feature['part_of']
        if feature['name'] != '' :
            name = feature['name']
        desc = ''
        if 'description' in feature:
            desc = feature['description']
        # create gpx waypoint
        type = 2
        # Create track in our GPX:
        gpx_track = gpxpy.gpx.GPXTrack( name=name, description= desc )
        gpx_out.tracks.append(gpx_track)

        # iterate over the segments

        for segment in segments:
            gpx_segment = gpxpy.gpx.GPXTrackSegment()
            gpx_track.segments.append(gpx_segment)
            for point in segment:
                gpx_segment.points.append(gpxpy.gpx.GPXTrackPoint(latitude=point.y(), longitude=point.x()))

    ensure_dir( export_dir )

    with open( export_dir + '/' + layer_name + '.gpx', 'w') as gpx_file:
        gpx_file.write( gpx_out.to_xml())



def export_wp_gpx_files( export_dir, layer_name, rw_id ):

    #this stuff should be in a configuration file

    nestbox = {
        'hihi': ['Navaid, Black', '26'],
        'saddleback': ['Navaid, Orange', '27'],
        'kakariki': ['Circle, Red', '28'],
        'rifleman': ['Circle, Green', '29'],
        'default': ['Navaid, blue', '72'],
        'files': True   # separate files please!
    }
    nestbox_default = 'Navaid, White',


    weeds = {
        'mp': ['Block, Blue', '0'],
        'sp': ['Flag, Blue', '0'],
        'mm': ['Diamond, Blue', '0'],
        'pw': ['Square, Blue', '0'],
        'default': ['Navaid, Blue', '0'],
        'files': False
    }
    weeds_default = 'Pin, Blue'
    test = 1
    markers = {  # by type
        'weed': weeds,
        'nb': nestbox,
        'sign': 'Pin, Green',
        'track': ['Flag, Red', 'track_wp']
    }

    # build a list of file from the config above

    files = []
    gpx_out = gpx_rw = None

    if rw_id == 'both' :
        gpx_out = {}
        gpx_rw = {}
    elif  rw_id == 'yes':
        gpx_rw = {}
    else :
        gpx_out = {}

    for k, v in markers.iteritems():
        if type(v) is dict  and v['files']:
            for  kk, vv in v.iteritems():
                if kk != 'files' and kk != 'default' :
                    files.append(kk)
        elif type(v) is list :
            files.append(v[1])
        else:
            files.append(k)

    files.append('all')

    for f in files:
        if gpx_out is not None:
            gpx_out[f] = gpxpy.gpx.GPX()
        if gpx_rw is not None:
            gpx_rw[f] = gpxpy.gpx.GPX()

    # set up CRS transform

    layer = find_layer(layer_name)
    if layer is None:
        print "Could not find layer '" + layer_name + "'"
        return False
    tr = create_transform_to_WGS84( layer )

    # iterate over features in layer

    for feature in layer.getFeatures():
        geom = feature.geometry()
        geom.transform(tr)
        point = geom.asPoint()

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
        elif type(m) is list: # filename given
            ftype = m[1]      # filename
            m = m[0]          # marker


        if ftype not in gpx_out:
            continue

        name = feature['name']
#        if rw_id and feature['rw_id'] !='' :
#            name = feature['rw_id']
        cmt = ''
        if feature['description']:
            cmt = feature['description']

        # create gpx waypoint

        if gpx_out is not None:
            wp = gpxpy.gpx.GPXWaypoint(latitude=point.y(), longitude=point.x(),
                                   name=name, comment=cmt, symbol=m[0], type=m[1])
            gpx_out[ftype].waypoints.append( wp )
            gpx_out['all'].waypoints.append( wp )
            # gpx_out[ftype].to_xml()

        if gpx_rw is not None:
            if feature['rw_id'] != NULL:
                name = feature['rw_id']

            wp = gpxpy.gpx.GPXWaypoint(latitude=point.y(), longitude=point.x(),
                                   name=name, comment=cmt, symbol=m[0], type=m[1])
            gpx_rw[ftype].waypoints.append( wp )
            gpx_rw['all'].waypoints.append( wp )

    # lastly wrirte out the files

    if gpx_out is not None:
        ensure_dir( export_dir )

    if gpx_rw is not None:
        ensure_dir( export_dir + '-rwid' )

    for file in files:
        if gpx_out  is not None:
            with open( export_dir + '/' + file + '.gpx', 'w') as gpx_file:
                gpx_file.write( gpx_out[file].to_xml())
        if gpx_rw  is not None:
            with open( export_dir + '-rwid/' + file + '.gpx', 'w') as gpx_file:
                gpx_file.write( gpx_rw[file].to_xml())

#def download_gpx_files( export_dir, devices):



def get_device_config( device_list ):

    devices = {}
    d = ''
    del_keys = []
    if os.path.exists(device_list):
        with open(device_list) as json_data:
            d = json.load(json_data)
            devices = d['devices']

    count =  0
    for dev, conf in devices.iteritems():
        #print 'device', dev
        if conf['type'] != 'directory':
            for item, val in d[conf['type']].iteritems():
                #print item, val
                conf[item] = val

        if 'top_dir' not in conf:
            continue
        found = False
        for dir in glob.glob(conf['top_dir']):
            id = ''
            with open(dir + '/Garmin/GarminDevice.xml', 'r') as f:
                for l in f:
                    m = re.search('<Id>(\d+)<\/Id>', l)
                    if m:
                        id = m.group(1)
                        if id == conf['id']:
                            conf['gpx_dir'] = dir+ '/' + conf['gpx_dir']
                            found = True
                            count += 1
        if not found:
            print "Can not find device " + id + " in devices file"
            del_keys.append(dev)

    if count == 0:
        print "No imput devices found"
    for key in del_keys:
        del devices[key]
    return devices

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

def import_gpx_files( new_dir, devices, upload ):

    new_files = './current/new_files'
    # keep_data_for = ' 6 months'

    archive = {}

    # copy all the files from the latest directory to new_dir and compute md5 for all gpx files

    if upload:
        ensure_dir(new_dir)
        try:
            os.remove('./current')
        except:
            pass
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

#        for device, gps_dir in get_device_config(gps_mount, 'devices.json' ).iteritems():
        for device, conf in devices.iteritems():

            # for each gpx file on the device  copy new or changed files to :new_files
            #   all have already been copied to
#            os.system( 'pwd' )
#            print device, gps_dir
#            p = re.compile(r'\.gpx$')

            dev_type = conf['type']

            gps_dir = ''
            if 'gpx_dir' in conf:
                gpx_dir = conf['gpx_dir']
            else:
                continue  # not an input device
            print "loading"
            for f in os.listdir( gpx_dir ):
                if re.search(r'\.gpx$', f):
                    fp = gpx_dir + '/' + f
                    ff = device + '-' + f
#                    print fp, ff
                    if ff not in archive or (archive[ff]['digest'].digest() != md5_file(fp).digest() ) :
                        sysx(['cp', '-p', fp, new_dir + '/' + ff])  # Copy it to new archive
                        os.symlink(  '../' + ff, new_files + '/' + ff )
#                        sysx(['cp', '-p', fp, new_files + '/' + ff])  # Copy it to :new_files for further processing

    # At this point we should have an archive copy of the GPX directory in new_dir
    # and a copy of all new/chagned files in :new_files
    # instantiate gpx object to hold new and changed objects

    wp_master = find_layer( 'wp_master' )
    tr = create_transform_to_WGS84(wp_master)

    changed = gpxpy.gpx.GPX()
    new = gpxpy.gpx.GPX()

    for f in os.listdir(new_files):

        if re.search(r'\.gpx$', f) and not re.match(r'(changed|new)', f):
            original = False
#            if f in archive:  # existing file -- read it so we can figure out what changed
#                original = {}
#                with open('latest/' + f, 'r') as gpx_file:
#                    try:
#                        gpx = gpxpy.parse(gpx_file)
#                    except:
#                        print "error parsing latest/" + f
#                        continue
#
#                    for wp in gpx.waypoints:
#                        original[wp.name] = wp
#            if f in archive:
#                next
            print f
            with open(new_files + '/' + f, 'r')  as gpx_file:
                try:
                    gpx = gpxpy.parse(gpx_file)
                except Exception as e:
                    print "error parsing " + new_files+ '/' + f
                    print e
                    continue
                first = True
                for wp in gpx.waypoints:
                    existing = wp_master.getFeatures(QgsFeatureRequest().setFilterExpression(u'"name" = \''+wp.name+"'"))
                    try: feature = existing.next()
                    except:
                        new.waypoints.append(wp)
                        continue
                    # have a existing waypoint with that name
                    diff = wp_diff( feature.geometry(), wp, tr, re.match(r'BT CH', wp.name )) # check if geometry matches
                    if diff > 0.00001:  # check if geometry matches
                        print 'updated', wp.name, diff
                        changed.waypoints.append(wp)

    if new.waypoints:
        with open(new_files +'/new.gpx', 'w') as output:
            output.write(new.to_xml())

    if changed.waypoints:
        with open(new_files + '/changed.gpx', 'w') as output:
            output.write(changed.to_xml())
    return [new.waypoints, changed.waypoints]
