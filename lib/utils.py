import sys, os, re, datetime

wp_type_d = {
    'R': 'rt',
    'B': 'nb',
    'S': 'sign',
    'T': 'track',
    'R': 'rt',
    'C': 'stream',
    'M': 'misc',
    'W': 'weed_site',
    'F': 'find',
    'P': 'poly',
    'M': 'misc'
}

date_re = re.compile(r'(\d\d)-(\w\w\w) (\d+):?(\d+)([ap])?')  # default name for eTrex SE

def get_wp_re( ):
    keys = ''.join(wp_type_d.keys())
    return re.compile(fr'([{keys}])')

def check_wp_type( name ):
    if name[0] in wp_type_d:
        return wp_type_d[name[0]]
    return None

wp_types = {
    'B': {
        'H': 'hihi',
        'T': 'saddleback',
        'K': 'kakariki',
        'R': 'rifleman'
    },
    'F': {'W' : 'weed'}
}
months = {
    'Jan': 1,
    'Feb': 2,
    'Mar': 3,
    'Apr': 4,
    'May': 5,
    'Jun': 6,
    'Jul': 7,
    'Aug': 8,
    'Sep': 9,
    'Oct': 10,
    'Nov': 11,
    'Dec': 12,
}

def wp_classes( type, name ):
    if type in wp_types and name[2] in wp_types[type]:
        return wp_types[type][name[2]]
    elif type == 'weed':
        return name[2:3]
    else:
        return None

def build_canon_name( wp, qgis_name, year):
    print( wp.name)
    # gps name should be in the form "dd-Mmm hh:mmad?"
    date = re.match(date_re, wp.name)
    yy = year % 100
    if date != None:
        m = months[date.group(2)]
        d = int(date.group(1))
        h = int(date.group(3))
        if date.group(5) == 'p' and h != 12:
            h += 12
        min = int(date.group(4))
    else:
        print( "name {wp.name} is not a date")
        return
    new_name = f"{qgis_name}-{yy}{format(m,'02d')}{format(d,'02d')}T{format(h,'02d')}{format(min,'02d')}"
    wp.time = datetime.datetime(year, m, d, h, min)
    wp.name = new_name
    print( f'{wp.name}:{wp}' )
