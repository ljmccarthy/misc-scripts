import re
import datetime
from cgi import escape
from collections import namedtuple
from urllib.parse import quote_plus
from urllib.request import urlopen
from bs4 import BeautifulSoup

base_url = 'http://krikzz.com/pub/support'

EverdriveOS = namedtuple('EverdriveOS', ['name', 'dir', 'changelist', 'bin_filename', 'ver_filename_re'])
Entry = namedtuple('Entry', ['title', 'version', 'date', 'changes', 'link'])

os_list = [
    EverdriveOS('Everdrive 64', '/ed64/os-bin', '/changelist.txt', '/OS-V{0}.zip', re.compile('^OS-V(\d+).zip')),
    EverdriveOS('Everdrive MD', '/everdrive-md/os-bin', '/changelist.txt', '/os-v{0}.bin', re.compile('^os-v(\d+).bin')),
    EverdriveOS('Everdrive MD v3', '/edmd-v3/OS', '', '/v{0}/MDOS.BIN', re.compile('^v(\d+)$')),
    EverdriveOS('Everdrive N8', '/everdrive-n8/OS', '/changelist.txt', '/nesos-v{0}.zip', re.compile('^nesos-v(\d+).zip$')),
    EverdriveOS('Master Everdrive', '/ms-everdrive/os-bin', '/chagelist.txt', '/os-v{0}.sms', re.compile('^os-v(\d+).sms$')),
    EverdriveOS('Mega Everdrive', '/mega-ed/OS', '/changelist.txt', '/V{0}/MEGAOS.bin', re.compile('^V(\d+)$')),
    EverdriveOS('Super Everdrive', '/super-everdrive/os-bin', '/chagelist.txt', '/os-v{0}.smc', re.compile('^os-v(\d+).smc$')),
    EverdriveOS('Super Everdrive v2', 'super-ed-v2/OS', '', '/snesos-v{0}.zip', re.compile('^snesos-v(\d+).zip$')),
    EverdriveOS('Turbo Everdrive', '/turbo-ed/os', '/changelist.txt', '/v{0}/tos.pce', re.compile('^v(\d+)$')),
]

re_changelist = re.compile(r'''
    \s*
    ^(nesos-)?[vV](?P<version>\d+)(:)?\s*
    ((date:\s*)?(?P<day>\d{2})\.(?P<month>\d{2})\.(?P<year>\d{4})\s*)?
    (?P<changes>(^(\d+\)|[+]).+\n\s*)+)
''', re.MULTILINE | re.VERBOSE)

feed_template = '''\
<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
<title>Everdrive OS Updates</title>
<link href="http://iogopro.com/feeds/everdrive.xml" rel="self" />
<link href="http://krikzz.com/" />
<updated>{updated}</updated>
{entries}
</feed>
'''

entry_template = '''\
<entry>
    <title>{0.title}</title>
    <link href="{0.link}" />
    <updated>{0.date}</updated>
    <content type="html"><pre>{0.changes}</pre></content>
</entry>
'''

def parse_changelist(s):
    for m in re_changelist.finditer(s):
        version = int(m.group('version'))
        date = '{year}-{month}-{day}T00:00:00Z'.format(**m.groupdict()) if m.group('year') else ''
        changes = '\n'.join(escape(x.strip()) for x in m.group('changes').split('\n') if x.strip())
        yield (version, date, changes)

def read_url(url):
    print('Fetching ' + url)
    with urlopen(url) as f:
        return f.read().decode('latin-1')

def dir_listing_url(path):
    return base_url + '/index.php?dir=' + quote_plus(path.lstrip('/'))

def make_entry(os, version, date='', changes=''):
    title = '{0} OS v{1}'.format(os.name, version)
    link = base_url + os.dir + os.bin_filename.format(version)
    return Entry(title, version, date, changes, link)

re_file_or_dir = re.compile('^(file|directory)$')

def get_feed_data():
    os_entries = []
    for os in os_list:
        versions_seen = set()
        if os.changelist:
            text = read_url(base_url + os.dir + os.changelist)
            for version, date, changes in parse_changelist(text):
                if date:
                    entry = make_entry(os, version, date, changes)
                    os_entries.append(entry)
                    versions_seen.add(entry.version)
        #soup = BeautifulSoup(read_url(dir_listing_url(os.dir)))
        #for tag in soup.find_all('a', {'class': re_file_or_dir}):
        #    m = os.ver_filename_re.match(tag.text)
        #    if m:
        #        version = int(m.group(1))
        #        if version not in versions_seen:
        #            os_entries.append(make_entry(os, version))
    os_entries.sort(key=lambda x: x.date, reverse=True)
    return os_entries

def generate_feed():
    updated = datetime.datetime.utcnow().isoformat('T') + 'Z'
    entries = ''.join(entry_template.format(entry) for entry in get_feed_data())
    feed_text = feed_template.format(updated=updated, entries=entries)
    return feed_text.encode('utf-8', 'xmlcharrefreplace')

if __name__ == '__main__':
    feed = generate_feed()
    with open('everdrive.xml', 'wb') as f:
        f.write(feed)
