# Pastrami

 ![Pastrami logo](pastrami.svg)

Pastrami is a secure, minimalist text storage for your sensitive data. It is designed to provide a quick and efficient way to store sensitive information, ensuring that each piece of data is encrypted using its own unique item ID as the encryption key. 

# Features
- **Memory-Only database**: Pastrami can operate entirely in memory, offering fast access and retrieval of encrypted text without persisting data to disk.
- **Item ID Encryption**: Each piece of text is encrypted using its corresponding item ID. This ensures that the encryption key is unique to each stored item, enhancing the security of your sensitive data.
 - **Simple and Lightweight**: The service is designed to be easy to use and does not impose unnecessary complexity. Integration with your applications or systems is straightforward.

# Getting started
To use the Pastrami web service, follow these steps:
```
git clone https://github.com/lamehost/pastrami.git
cd pastrami
poetry install
```
After Pastrami is installed, you can launch it as follows:
```
cp pastrami.conf.sample pastrami.conf
poetry run pastrami
```

## CLI arguments
By default Pastrami binds to port 8080 on localhost. Settings can be changed via CLI:
```
$ poetry run pastrami -h
usage: pastrami [-h] [-d] [HOST] [PORT]

A lightweight solution for securely storing encrypted text.

positional arguments:
  HOST         Host to bind to. Default: 127.0.0.1
  PORT         Port to bind to. Default: 8080

options:
  -h, --help   show this help message and exit
  -d, --debug  Turns uviconr debugging on

Configuration file name is hardcoded: pastrami.conf
```

## Docker
To use pastrami with Docker or Podman, follow these steps:
```
podman build -t pastrami:latest .
cp pastrami.conf.sample pastrami.conf
podman run -it --rm -p 8080:8080 -v $(pwd)/pastrami.conf:/tmp/pastrami.conf pastrami -d
```

# Usage
Access web frontend at http://localhost:8080. Write text and hit ctrl+s to save.

## API endpoints
You can use API endpoints to save and retrieve text. If *pastrami_docs* is set to true in *pastrami.conf*, then swagger is available at http://localhost:8080/docs/.

## Formatting options:
By default Text content is formated as HTML page and colorized with *Google Code Prettify* stylesheet. Other formatting options can be returned by attaching an extension at the end of the URL:
 - **No extension**: Google Code Prettify (default)
 - **.txt**: Regular text file
 - **.md**: Content is interpreted as Markdown and rendered as HTML
