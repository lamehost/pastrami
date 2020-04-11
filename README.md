# Pastrami

Pastebin service.

# Install
The easyest way to install Pastrami is via PIP
```
virtualenv pastrami
cd pastrami
source bin/activate
pip install git+https://github.com/lamehost/pastrami.git
```

# Apache WSGI
Best way to run Pastrami is to run it as a WSGI application on Apache.  
First you create your own application as below:
```
#!/usr/bin/env python

from pastrami.webapp
import application
```

Then you configure apache as follows (assuming application is named after *apache.wsgi*):
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
API's are documented via Swagger at */api/2.0/ui*
