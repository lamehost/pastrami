# Pastrami

Text pasting service.

# Install
The easyest way to install Pastrami is via PIP
```
virtualenv pastrami
cd pastrami
source bin/activate
pip install git+https://github.com/lamehost/pastrami.git
```

# Apache WSGI
In case you want to integrate Pastrami as WSGI in Apache, here's a snippet you can use.  
```
#!/usr/bin/python

from __future__ import absolute_import
from __future__ import print_function

import os

from flask import current_app

from pastrami.configuration import get_config
from pastrami.pastrami import APP

# Get config file
config_file = os.environ.get('config', 'pastrami.conf')

# Read config
config = get_config(config_file)

# Configure app
with APP.app_context():
    for key, value in config.items():
        current_app.config[key] = value
```

You can save the above as ''pastrami.wsgi'' and configure your site as follows:
```
<VirtualHost *:80>
    ServerAdmin webmaster@example.com
    ServerName p.example.com

    WSGIDaemonProcess pastrami user=www-data group=www-data threads=5 python-home=/var/www/vhosts/p.example.com/
    WSGIScriptAlias / /var/www/vhosts/p.example.com/pastrami.wsgi

    LimitRequestBody 2048000

    <Directory /var/www/vhosts/p.example.com/>
        WSGIProcessGroup pastrami
        WSGIApplicationGroup %{GLOBAL}
        WSGIPassAuthorization On
        WSGIScriptReloading On
        Order deny,allow
        Allow from all
    </Directory>
</VirtualHost>
```

# Swagger
API's are documented via Swagger at ''/doc''
