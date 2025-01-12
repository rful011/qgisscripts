
# =========== main line =================

repository  = '/Users/rful011/GPS-Data'
new_dir = './' + time.strftime("%Y-%m-%d")
mount = '/Volumes'

parser = argparse.ArgumentParser(description='upload and process gpx files')
parser.add_argument('-U', '--noupload', help="don't upload files -- they already have been", action="store_true" )
parser.add_argument('-m', '--mount', help="mount points for GPS file systens", action="store" )
parser.add_argument('-r', '--repository', help="base dir where the GPX files are", action="store" )
parser.add_argument('-n', '--new_dir', help="dir where we put new/changed files", action="store" )
args = parser.parse_args()

print( 'args ', args )

print(">>>>>", sys.exit )

upload = not args.noupload
if args.mount:
    mount = args.mount
if args.repository:
    repository = args.repository
if args.new_dir:
    new_dir = args.new_dir

process_gpx_files( repository, new_dir, mount, upload )
