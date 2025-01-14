# Pull the official Python base image
FROM python:3.12-slim-bullseye

# Set work directory
WORKDIR /usr/src/app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install ffmpeg libsm6 libxext6  -y    

# Upgrade pip and install dependencies
RUN pip install --upgrade pip
COPY ./requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Create a script to run migrations and create a superuser
RUN echo "#!/bin/bash \n\
python manage.py migrate --noinput \n\
python manage.py createsuperuser --noinput --username \$DJANGO_SUPERUSER_USERNAME --email \$DJANGO_SUPERUSER_EMAIL \n\
exec python manage.py runserver 0.0.0.0:8000" > /start.sh && chmod +x /start.sh

# Set the default command to run the script
CMD ["/start.sh"]

# # Set the default command to run your application
# CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]