# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies that might be needed by Python packages
# For example, gcc and other build tools if a package needs to compile from source.
# This is a good practice, though may not be strictly necessary for this set of requirements.
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
# --no-cache-dir ensures that pip doesn't store downloaded packages, keeping the image size down.
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container at /app
COPY . .

# Creates a directory for the database and logs if they don't exist
# and sets the correct permissions
RUN mkdir -p /app/data /app/logs && \
    chown -R www-data:www-data /app/data /app/logs

# Run the application
CMD ["python", "main.py"]
