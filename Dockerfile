FROM alpine:3.7 as system

# Install uwsgi
RUN apk add --no-cache git python3 py3-gunicorn


FROM system

# Install pastrami
RUN pip3 install --no-cache-dir git+https://github.com/lamehost/pastrami.git

# Expose HTTP server port
EXPOSE 8080

# Prepare environment
RUN mkdir /app
RUN chown -R nobody /app
WORKDIR /app


# Run pastrami
USER nobody
CMD ["gunicorn", "-b", "0.0.0.0:8080", "pastrami.webapp:application"]
