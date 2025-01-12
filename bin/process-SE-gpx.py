import sys, os, re, argparse
import gpxpy
import gpxpy.gpx
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lib'))
sys.path.append('/usr/local/lib/python3.7/site-packages')

from utils import *

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lib'))
sys.path.append('/usr/local/lib/python3.9/site-packages')

def process_se_gpx_files( raw_dir, new_dir ):

    type_re = get_wp_re()

    pattern = re.compile(r'\.gpx$', re.IGNORECASE )
    # Iterate over the sorted files
    now = datetime.now()
    year = now.year
    for file_name in sorted(os.listdir(raw_dir)):
        # Check if the file name matches the regular expression
        print(f'file: "{file_name}" ')
        y = input(f'Enter year dddd for this file (default {year}:')
        if y != None:
            year = int(y)
        if pattern.search(file_name):
            name = None
            gpx_fn = raw_dir + '/' + file_name
            with open(gpx_fn, 'r', encoding='utf8') as gpx_file:
                try:
                    gpx = gpxpy.parse(gpx_file)
                except Exception as e:
                    print(f"error parsing {gpx_fn}: {e}")
                    continue
                first = True
                new = True
                prompt = True
                for wp in gpx.waypoints:
                    prompt = True
                    while prompt:
                        name_n = input( f'WP Name: {wp.name}, wp name:{name}: ')
                        if name_n != '':
                           name = name_n
                           new = True
                        if name == None:
                            print("must give a name", file=sys.stderr)
                        else :
                            prompt = False
                        if not check_wp_type(name):

                            print(f"'{name}' is not valid. Try again...", file=sys.stderr)
                            prompt = True
                        else :
                            c_name = build_canon_name(wp, name, 2024 )

# =========== main line =================

from time import localtime, strftime
from datetime import datetime, timezone
from dateutil.parser import parse

date = datetime.now().strftime("%Y-%m-%d")

from os.path import expanduser, exists

time = datetime.now() # current date and time
base_repository  = '/Users/rful011/GPS-Data/'
new_dir =  base_repository + time.strftime("%Y-%m-%d")
raw_dir = base_repository + 'raw'

parser = argparse.ArgumentParser(description='Process gpx files from eTex SE')
parser.add_argument('-r', '--raw', help="base dir where the GPX files are", action="store" )
parser.add_argument('-n', '--new_dir', help="dir where we put new/changed files", action="store" )
args = parser.parse_args()

print( 'args ', args )

# print(">>>>>", sys.exit )

if args.raw:
    raw_dir = args.raw
if args.new_dir:
    new_dir = args.new_dir

process_se_gpx_files( raw_dir, new_dir )
