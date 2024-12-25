# *** Base ***
FROM python:3.10.4-slim

# Metatada
EXPOSE 8080/tcp
LABEL org.opencontainers.image.authors="Marco Marzetti <marco@lamehost.it>"
LABEL org.opencontainers.image.url="https://github.com/lamehost/pastrami"

# Copy script
COPY pastrami /pastrami
COPY README.md /

# Install pastrami
COPY pyproject.toml /pyproject.toml
COPY poetry.lock /poetry.lock
RUN pip install --no-cache-dir poetry \
  && poetry config virtualenvs.create false \
  && poetry install --no-interaction --no-ansi

# Restrict permissions
USER nobody
WORKDIR /tmp

# Run script
ENTRYPOINT ["pastrami", "0.0.0.0"]

# Healtcheck
HEALTHCHECK CMD ["curl", "--fail", "http://localhost:8080", "||", "exit", "1"]
