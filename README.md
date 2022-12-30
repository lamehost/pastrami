# Pastrami
Pastebin web service.  

On the web GUI text is saved with ctrl+s. By default it applies the *Google Code Prettify* stylesheet to the content. A text file can be generated by adding *.txt* at the end of the URL.

# Install
The easyest way to install Pastrami is via PIP
```
git clone https://github.com/lamehost/pastrami.git
cd pastrami
poetry build
pip install dist/aggregate_prefixes-1.1.0-py3-none-any.whl
```

# Formatting options:
Content can be formatted as follows:
 - **Google Code Prettify**: Default.
 - **No formatting**: Append `.txt` at the end of the URL
 - **Markdown**: Append `.md` at the end of the URL
