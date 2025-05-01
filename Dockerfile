FROM python:3.10-slim

#ARG INVESTGPT_TOKEN

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    gnupg \
    ffmpeg \
 && rm -rf /var/lib/apt/lists/*

# Install doppler cli
#RUN curl -Ls --tlsv1.2 --proto "=https" --retry 3 https://cli.doppler.com/install.sh | sh

# Set the working directory in the container
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container at /app
COPY . .

#RUN chmod +x set_build_version.sh
#RUN ./set_build_version.sh

# Setup doppler
#RUN doppler configure set token ${INVESTGPT_TOKEN}

# Make port 8001 available to the world outside this container
EXPOSE 8001

# Run the application
#CMD ["doppler", "run", "--", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]
