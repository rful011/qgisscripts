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
    export_dir = './current/gpx'
    just_finalise = False
    rw_id = ('', yes, both)  # use full name as default

"""

from time import localtime, strftime
import sys, os, re
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lib'))

from os.path import expanduser
from my_utils import export_wp_gpx_files, export_track_gpx_files

def run_script(iface, **myargs): # layer, repository, finalise  ):

    wp_layer = 'wp_master'
    repository = expanduser('~') +"/GPS-Data"
    finalise = False
    track_layer = 'Tracks'
    export_dir = './current/gps-export'
    just_finalise = False
    rw_id = ''  # use full name as default
    exit_now = False
    for k, v in myargs.iteritems():
        if re.match(k, 'wp'):
            wp_layer = v
        elif re.match( k, 'track' ) :
            track_layer = v
            tracks = True
        elif re.match( k, 'repository' ):
            repository = v
        elif re.match( k, 'just_finalise'):
            just_finalise = v
            finalise = True
        elif re.match(k, 'finalise'):
            finalise = v
        elif re.match(k, 'rw_id'):
            rw_id = v
        elif re.match(k, 'export'):
            export_dir = v
        elif re.match(k, 'help'):
            print "repository = ~/GPS-Data, layer = wp_master, finialise = False, rw_id = False, just_finailise = False"
            exit_now = True
        else:
            print "I don't recognise option '" + k + "'"
            exit_now = True

    if exit_now:
        return

    os.chdir(repository)

    if not just_finalise:
        if wp_layer != '':
            export_wp_gpx_files( export_dir, wp_layer, rw_id )
        if track_layer != '':
            export_track_gpx_files( export_dir, track_layer )

    if finalise :  # change the symlinks ready for next update with latest pointing to most recent dir
        os.remove('latest')
        os.rename('current', 'latest')