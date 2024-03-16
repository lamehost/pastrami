# *** Base ***
FROM python:3.10.4-slim

# Copy script
ADD pastrami /pastrami
ADD README.md /

# Install pastrami
ADD pyproject.toml /pyproject.toml
ADD poetry.lock /poetry.lock
RUN pip install --no-cache-dir poetry
RUN poetry config virtualenvs.create false \
  && poetry install --no-interaction --no-ansi

# Restrict permissions
USER nobody
WORKDIR /tmp

# Run script
ENTRYPOINT ["pastrami", "0.0.0.0"]

# Healtcheck
HEALTHCHECK CMD curl --fail http://localhost:8080 || exit 1 
