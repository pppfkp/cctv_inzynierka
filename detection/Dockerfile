# Use the official NVIDIA PyTorch image
FROM ultralytics/ultralytics:8.3.57

# Set the working directory
WORKDIR /usr/src/app

# Upgrade pip and install dependencies
RUN pip install --upgrade pip
COPY ./requirements.txt .
RUN pip install --no-deps --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Run both Python scripts (stream.py in the background)
CMD python stream.py & python process_frame.py

# windows

# docker run --gpus all -it `
#     -v ${PWD}:/usr/src/app `
#     --network bridge `
#     -p 5000:5000 `
#     --env-file .env `
#     flask-ultralytics-gpu 

# docker build -t flask-ultralytics-gpu .    

# inside the container
# pip freeze | grep -v "@" > requirements.txt

# docker tag flask-ultralytics-gpu pppfkp15/flask-ultralytics-gpu:3.0