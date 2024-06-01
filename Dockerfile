# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy the current directory contents into the container at /usr/src/app
COPY . .

# Install any needed dependencies specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
RUN apt-get update -y
RUN apt-get upgrade -y
RUN apt-get install ffmpeg -y
# Run the bot when the container launches
CMD ["python", "musicbot.py"]
