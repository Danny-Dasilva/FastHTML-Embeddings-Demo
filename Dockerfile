# Use a minimal Python image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

# Copy only requirements to cache them in docker layer
COPY pyproject.toml poetry.lock* /app/

# Project initialization:
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

# Copy project
COPY . /app

EXPOSE 5001
COPY wait-for-it.sh /wait-for-it.sh
RUN chmod +x /wait-for-it.sh

# Set the default command to start a shell


# # Set the default command to wait for the database and then run your scripts
CMD ["/bin/bash", "-c", "sleep 10 && poetry run python embeddings.py && poetry run python main.py"]