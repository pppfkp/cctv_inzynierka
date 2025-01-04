# Use the official NVIDIA PyTorch image
FROM ultralytics/ultralytics:8.3.57

# Set the working directory
WORKDIR /usr/src/app

# # Upgrade pip and install dependencies
# RUN pip install --upgrade pip
# COPY ./requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

# Upgrade pip and install dependencies
RUN pip install --upgrade pip
COPY ./requirements.txt .
RUN pip install --no-deps --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

CMD bash

# docker run --gpus all -it \
#   -v $(pwd):/usr/src/app \
#   --network bridge \
#   -p 5000:5000 \
#   pytorch-nvidia-smi

# docker run --gpus all -it `
#   -v ${PWD}:/usr/src/app `
#   --network bridge `
#   -p 5000:5000 `
#   pytorch-nvidia-smi

# docker build -t pytorch-nvidia-smi .    

# pip freeze | grep -v "@" > requirements.txt