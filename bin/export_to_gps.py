"""
    takes a layer (normally wp_master) and produces a number separate GPX files
    the makers and which points get exported are controlled by a set of dictionaries
    Currently these are hard coded but when I set this up as a proper plugin I will
    allow a config file as a parameter or figure some better way of handling this

    :parameters:

    wp_layer = 'wp_master'
    repository = expanduser('~') +"/GPS-Data"
    finalise = False
    track_layer = 'Tracks'
    export_dir = './current/gpx-export'
    just_finalise = False
    rw_id = ('', yes, both)  # use full name as default

"""

from time import localtime, strftime
import sys, os, re, glob
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lib'))

from os.path import expanduser, isfile
from my_utils import export_wp_gpx_files, export_track_gpx_files, get_device_config, sysx, set_def


def run_script(iface, **myargs): # layer, repository, finalise  ):

    repository = expanduser('~') + "/Google Drive/Tiri/GPX repository"

    mount = changed = new = export_dir = archive = wp_layer = line_layers = None
    just_finalise = finalise = False
    rw_id = None  # use full name as default
    exit_now = False
    for k, v in myargs.items():
        print( k, v)
        if re.match(k, 'wp'):
            wp_layer = v
        elif re.match( k, 'track' ) :
            track_layer = v
            tracks = True
        elif re.match( k, 'repository' ):
            repository = expanduser('~') + v
        elif re.match( k, 'just_finalise'):
            just_finalise = v
            finalise = True
        elif re.match(k, 'finalise'):
            finalise = v
        elif re.match(k, 'rw_id'):
            rw_id = v
        elif re.match(k, 'export'):
            export_dir = v
            print( k, v, export_dir )
        elif re.match(k, 'help'):
            print( "repository = ~/GPS-Data, layer = wp_master, finialise = False, rw_id = False, just_finailise = False" )
            exit_now = True
        else:
            print( "I don't recognise option '" + k + "'" )
            exit_now = True

    if exit_now:
        return


    os.chdir(repository)
    config = get_device_config( 'devices.json' )
    defaults = config[1]
    devices = config[0]

    wp_layer = set_def( wp_layer, defaults, 'master', "wp_master")
    archive = set_def( archive, defaults, 'archive', "~/GPS-Data")
    new = set_def( new, defaults, 'new', 'new')
    changed = set_def(changed,  defaults, 'changed', "changed")
    mount = set_def( mount, defaults, 'mount', "/Volumes" )
    export_dir = set_def( export_dir, defaults, 'export_dir', 'gpx-export')
    line_layers = set_def(line_layers, defaults, 'line_layers', ['Tracks', 'Streams'])

    if not just_finalise:
        if wp_layer != '':
            export_wp_gpx_files( './current/' + export_dir, wp_layer, rw_id )
        for l in line_layers:
            m = re.search( r'(\w+)/(\w+)', l )
            print( l, m.group(1), m.group(2) )
            export_track_gpx_files( './current/' + export_dir, m.group(1), m.group(2) )

    save_dir = os.getcwd()
    if finalise :  # update the export stuff
        os.chdir('./current/'+ export_dir)
        for device, conf in devices.items():
            if 'export' not in conf:
                continue

            print( ' '.join(conf['export']) )
            fglob = []
            for file in conf['export']:
                fglob += glob.glob(file)
            print( fglob )

            if 'clean' in conf:  # remove existing files from export dir
                remove = glob.glob(conf['gpx_dir']+'/*.gpx')
                if len(remove) > 0:
                    sysx( ['rm'] +  glob.glob(conf['gpx_dir']+'/*.gpx') )
            # and copy in the new ones
            sysx(['cp'] + fglob + [conf['gpx_dir']])
## and change the symlinks ready for next update with latest pointing to most recent dir
        os.chdir(save_dir)
        os.remove('latest')
        os.rename('current', 'latest')
        # copy the files to the devices


