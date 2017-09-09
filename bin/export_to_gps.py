"""
    takes a layer (normally wp_master) and produces a number separate GPX files
    the makers and which points get exported are controlled by a set of dictionaries
    Currently these are hard coded but when I set this up as a proper plugin I will
    allow a config file as a parameter or figure some better way of handling this
"""

from time import localtime, strftime
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lib'))

from my_utils import export_gpx_files

def run_script(iface, layer, repository, finalise  ):

    if layer == '':
        layer = 'wp_master'
    if repository == '' :
        repository = '/Users/rful011/GPS-Data'
    if finalise == '':
        finalise = False

    os.chdir(repository)

    export_gpx_files( layer )

    if finalise :  # change the symlinks ready for next update with latest pointing to most recent dir
        os.delete('latest')
        os.rename('current', 'latest')