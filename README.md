# Pastrami
Pastebin web service.  

Type text and save it with `ctr+s`.

# Install
The easyest way to install Pastrami is via PIP
```
git clone https://github.com/lamehost/pastrami.git
cd pastrami
poetry build
pip install dist/aggregate_prefixes-1.1.0-py3-none-any.whl
```

# Formatting options:
By default content is returned in an HTML page and colorized with *Google Code Prettify* stylesheet. Other formatting options can be returned by attaching an extension at the end of the URL:
 - **No extension**: Google Code Prettify (default)
 - **.txt**: Regular text file
 - **.md**: Content is interpreted as Markdown and rendered as HTML
