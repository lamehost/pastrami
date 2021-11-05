FROM python:3.9.7-slim-buster as system

# Install uwsgi
RUN pip install --no-cache-dir gunicorn==20.1.0

FROM system

# Install pastrami
ADD pastrami /pastrami
ADD pastrami.conf /pastrami.conf
ADD requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

# Expose HTTP server port
EXPOSE 8080

# Run pastrami
USER nobody
CMD ["gunicorn", "-b", "0.0.0.0:8080", "pastrami.webapp:create_app('/pastrami.conf')"]
