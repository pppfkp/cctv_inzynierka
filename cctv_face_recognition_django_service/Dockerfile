# Use a smaller CUDA image with runtime support
FROM nvidia/cuda:12.1.0-cudnn8-runtime-ubuntu20.04

# Set work directory
WORKDIR /usr/src/app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV DEBIAN_FRONTEND=noninteractive 

RUN apt-get update && DEBIAN_FRONTEND=noninteractive \
    apt-get install -y software-properties-common && \
    DEBIAN_FRONTEND=noninteractive add-apt-repository -y ppa:deadsnakes/ppa && \
    apt-get install -y python3.12 curl && \
    curl -sS https://bootstrap.pypa.io/get-pip.py | python3.12

RUN curl -sSL https://install.python-poetry.org | python3.12 - 
RUN pip3 install --upgrade requests
RUN ln -fs /usr/bin/python3.12 /usr/bin/python

RUN apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*


COPY ./requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Set the default command to run your application
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
