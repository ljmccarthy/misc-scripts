#!/usr/bin/env python3
#
# Downloads Postfix CIDR block list for China and Korea
# by Luke McCarthy 2013-12-12
#
# See: http://www.fadden.com/techmisc/asian-spam.htm

import re
from urllib.request import urlopen

with urlopen('http://okean.com/sinokoreacidr.txt') as f:
    data = f.read()

data = re.sub(' (China|Korea)$', ' REJECT', data.decode('ascii'), flags=re.M)

with open('/etc/postfix/sinokorea.cidr', 'wb') as f:
    f.write(data.encode('ascii'))

print('sinokorea cidr updated succesfully!')
