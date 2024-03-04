# Pastrami
Secure pastebin web service.  

Type text and save it with `ctr+s`.

# Install
The easyest way to install Pastrami is via poetry
```
git clone https://github.com/lamehost/pastrami.git
cd pastrami
poetry install
```

## Run
After Pastrami is installed, you can launch it as follows:
```
cp pastrami.conf.sample pastrami.conf
poetry run python -m pastrami
```
By default it binds to host 127.0.0.1 port 8080.

## Syntax
Default HTTP settings can be changed via CLI arguments:
```
$ poetry run python -m pastrami -h
usage: pastrami [-h] [-d] [HOST] [PORT]

Secure pastebin web service.

positional arguments:
  HOST         Host to bind to. Default: 127.0.0.1
  PORT         Port to bind to. Default: 8080

options:
  -h, --help   show this help message and exit
  -d, --debug  Turns uviconr debugging on

Configuration file name is hardcoded: pastrami.conf

```

# Formatting options:
By default content is returned in an HTML page and colorized with *Google Code Prettify* stylesheet. Other formatting options can be returned by attaching an extension at the end of the URL:
 - **No extension**: Google Code Prettify (default)
 - **.txt**: Regular text file
 - **.md**: Content is interpreted as Markdown and rendered as HTML
