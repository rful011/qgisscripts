
# Import the PyQt and the QGIS libraries
# Import the PyQt and the QGIS libraries
from PyQt5.QtCore import *
from PyQt5.QtGui import *
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

from datetime import timezone

def utc_to_local(utc_dt):
    return utc_dt.replace(tzinfo=timezone.utc).astimezone(tz=None)

# set parameter defaults


def set_def(item, conf, key, hc_def=None):
    if item:
        return item
    if key in conf:
        return conf[key]
    return hc_def


def find_layer( layer_name ):
    prog = QgsProject.instance()
    layer = prog.mapLayersByName( layer_name )
    print( layer_name, layer )
    if len(layer) == 0 :
        return None
    return layer[0]

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
        print ( lat, wp2.latitude, long, wp2.longitude, math.sqrt(diff1**2 + diff2**2 ) )
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
    tr = create_transform('to', model )
    # source crs
    crsSrc = QgsCoordinateReferenceSystem(4326)
    crsDest = model.crs()
    # tr = QgsCoordinateTransform(crsSrc, crsDest, QgsProject.instance() )

    vl = QgsVectorLayer("Point?crs="+crsDest.authid(), layer_name, "memory")
    pr = vl.dataProvider()  # need to create data provider

    fields = model.fields()

    if fields[0].name() == 'gid':
        fields.remove(0)  # let postgis set the gid
    pr.addAttributes(fields)
    vl.updateFields()  # tell the vector layer to fetch changes from the provider

    vl.updateFields()  # tell the vector layer to fetch changes from the provider
    fields = vl.fields()

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
        if wp.time:   # gpxpy returns times in UTC
            time =  utc_to_local(wp.time).strftime("%Y-%m-%d %T")
        fet = QgsFeature()
        fet.setFields(fields, True)

        point = QgsPoint( wp.longitude, wp.latitude)
        point.transform(tr)
        fet.setGeometry(QgsGeometry(QgsPoint( point.x(), point.y(), 0.0)))

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
    print ( layer_name, QgsProject.instance().addMapLayer(vl) )
#    print ( layer_name, QgsProject.layerStore(QgsProject.instance()).addMapLayer(vl) )

def create_transform( dir, layer, epsg = '4326' ):
    if dir == 'from':
        crsDst = QgsCoordinateReferenceSystem('EPSG:' + epsg)
        crsSrc = layer.crs()
    elif dir == 'to':
        crsSrc = QgsCoordinateReferenceSystem('EPSG:' + epsg )
        crsDst = layer.crs()
    else:
        return None
#    print(crsSrc, crsDst)
    return QgsCoordinateTransform( crsSrc, crsDst, QgsProject.instance() )


def export_track_gpx_files( export_dir, layer_name, name_by ):

    #this stuff should be in a configuration file

    gpx_out = gpxpy.gpx.GPX()

    # set up CRS transform

    layer = find_layer(layer_name)
    if layer is None:
        print ( "Could not find layer '" + layer_name + "'" )
        return False
    tr = create_transform( 'from', layer )

    # iterate over features in layer

    for feature in layer.getFeatures():
        # make sure there is one item of geometry
        geom = feature.geometry()
        geom.convertToMultiType()
        geom.transform(tr)
        segments = geom.asMultiPolyline()

        name = ''
        if name_by != 'none':  # then use the group by default
            name = feature[name_by]
        if name == '' and feature['name'] != '' :
            name = feature['name']
        desc = ''
        if 'description' in feature:
            desc = feature['description']
        # create gpx item
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
        gpx_file.write( gpx_out.to_xml()) # extra_attributes = garmin_attribs))



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

    for k, v in markers.items():
        if type(v) is dict  and v['files']:
            for  kk, vv in v.items():
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
        print ( "Could not find layer '" + layer_name + "'" )
        return False
    tr = create_transform( 'from',  layer )

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
            if feature['rw_id'] != None:
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

    garmin_attribs = {
        ('xmlns', "http://www.topografix.com/GPX/1/0"),
        ('xmlns:gpxx', "http://www.garmin.com/xmlschemas/GpxExtensions/v3"),
        ('xmlns:gpxtrkx', "http://www.garmin.com/xmlschemas/TrackStatsExtension/v1"),
        ('xmlns:wptx1', "http://www.garmin.com/xmlschemas/WaypointExtension/v1"),
        ('xmlns:gpxtpx', "http://www.garmin.com/xmlschemas/TrackPointExtension/v1"),
        ('xsi:schemaLocation', "http://www.topografix.com/GPX/1/0 http://www.topografix.com/GPX/1/0/gpx.xsd")
    }


    for file in files:
        if gpx_out  is not None:
            with open( export_dir + '/' + file + '.gpx', 'w', encoding='utf8') as gpx_file:
                print( file )
                gpx_file.write( gpx_out[file].to_xml( extra_attributes = garmin_attribs))
        if gpx_rw  is not None:
            with open( export_dir + '-rwid/' + file + '.gpx', 'w', encoding='utf8') as gpx_file:
                gpx_file.write( gpx_rw[file].to_xml(extra_attributes = garmin_attribs))

#def download_gpx_files( export_dir, devices):



def get_device_config( device_list ):

    devices =  {}
    default = {}
    d = ''
    del_keys = []
    if os.path.exists(device_list):
        with open(device_list) as json_data:
            d = json.load(json_data)
            devices = d['devices']
            default = d["defaults"]

    count =  0
    for dev, conf in devices.items():
        #print ( 'device', dev )
        if conf['type'] != 'directory':
            for item, val in d[conf['type']].items():
                #print ( item, val )
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
                                print ( "Can not find device " + id + " in devices file" )
                                del_keys.append(dev)
                                continue
        if not found:
            print( "Can not find device " + dev )
            del_keys.append(dev)

    if count == 0:
        print ( "No imput devices found" )
        return {}
    for key in del_keys:
        del devices[key]
    return [devices, default ]

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

def import_gpx_files( new_dir, devices, upload, from_time ):

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

        for device, conf in devices.items():  # iterate over devices in conf file
            dev_type = conf['type']
            gps_dir = ''
            if 'import' in conf:   # do we want to import from this device?
                gpx_dir = conf['gpx_dir']
            else:
                continue  # not an input device
            print ( "loading from ", gpx_dir )
            for f in os.listdir( gpx_dir ):  # iterate over the gpx files in gpx dir
                if re.search(r'\.gpx$', f):  # A GPX file
                    fp = gpx_dir + '/' + f
                    ff = device + '-' + f  # add dev prefix
                    if not re.search(r'-(Track | Wayp). +\.gpx$', f ):  # not created by GPS -- GARMIN specific
#                    print ( fp, ff )
                        original = './latest/gpx-export/'+f
                        print ( original )
                        if os.path.exists(original):  # it one of ours
                            print ( md5_file(fp).digest(), md5_file(original).digest() )
                            if md5_file(fp).digest() == md5_file(original).digest():  # The same ?
                                continue  # dont copy it
                        sysx(['cp', '-p', fp, new_dir + '/' + ff])  # Copy it to new archive

    # At this point we should have an archive copy of the GPX directory in new_dir
    # and a copy of all new/chagned files in :new_files
    # instantiate gpx object to hold new and changed objects

    wp_master = find_layer( 'wp_master' )
    wp_features = {}
    tr = create_transform( 'to', wp_master)


    changed = gpxpy.gpx.GPX()
    new = gpxpy.gpx.GPX()

    distance = QgsDistanceArea()  # instantiate distance object

    if new.waypoints:
        with open(new_files +'/new.gpx', 'w', encoding='utf8') as output:
            output.write(new.to_xml()) # extra_attributes = garmin_attribs))


    for f in wp_master.getFeatures():   # cache all featutes
        # print ( f.attribute('name') )
        wp_features[f.attribute('name')] = f

    for f in os.listdir(new_dir):
        if re.search(r'\.gpx$', f) and not re.match(r'(changed|new)', f):
            original = False
            print ( 'new_dir:', f )
            with open(new_dir + '/' + f, 'r', encoding='utf8')  as gpx_file:
                try:
                    gpx = gpxpy.parse(gpx_file)
                except Exception as e:
                    print ( "error parsing " + new_files+ '/' + f )
                    print ( e )
                    continue
                first = True
                for wp in gpx.waypoints:
                    if from_time and wp.time > from_time:
                        continue
                    if wp.name in wp_features: # have a existing waypoint with that name
                        continue
                        feature = wp_features[wp.name]
                        new_point = QgsPoint( wp.longitude, wp.latitude)
                        print( new_point, tr)
                        new_point.transform(tr)
                        diff =  distance.measureLine( feature.geometry().asPoint(), QgsPointXY(new_point) )
                        if diff >= 0.1:  # check if geometry matches
                            print ( 'updated', wp.name, diff )
                            changed.waypoints.append(wp)
                    else:
                        new.waypoints.append(wp)

#    if changed.waypoints:
#        with open(new_files + '/changed.gpx', 'w') as output:
#            output.write(changed.to_xml()) # extra_attributes = garmin_attribs))
    return [new.waypoints, changed.waypoints]
