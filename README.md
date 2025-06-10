### 1. Dockerfile for Flask Application

Create a file named `Dockerfile` in your project directory (where `server.py` is located):

```dockerfile
# Dockerfile
FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Expose the port the app runs on
EXPOSE 5000

# Command to run the application
CMD ["python", "server.py"]
```

### 2. Nginx Configuration

Create a file named `nginx.conf` in your project directory:

```nginx
# nginx.conf
server {
    listen 80;

    server_name admin.aliislamic.org;

    location / {
        proxy_pass http://flask_app:5000/admin;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

server {
    listen 80;

    server_name party.aliislamic.org;

    location / {
        proxy_pass http://flask_app:5000/party;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 3. Docker Compose File

Create a file named `docker-compose.yml` in your project directory:

```yaml
version: '3.8'

services:
  flask_app:
    build: .
    restart: always
    environment:
      - SERVER_IP=0.0.0.0
      - SERVER_PORT=5000
      - NGROK_LINK=http://localhost:5000/party  # Update this if needed
    volumes:
      - .:/app
    expose:
      - "5000"

  nginx:
    image: nginx:latest
    restart: always
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf
    depends_on:
      - flask_app
```

### 4. Directory Structure

Your project directory should look like this:

```
/home/akimovsarvar/Projects/Party-Night/
│
├── Dockerfile
├── docker-compose.yml
├── nginx.conf
├── requirements.txt
├── server.py
└── (other files and directories)
```

### 5. Running the Setup

1. Make sure you have Docker and Docker Compose installed on your machine.
2. Navigate to your project directory in the terminal.
3. Run the following command to build and start the services:

```bash
docker-compose up --build
```

### 6. DNS Configuration

Make sure that the DNS records for `admin.aliislamic.org` and `party.aliislamic.org` are pointing to the IP address of the server where this Docker setup is running.

### 7. Accessing the Application

Once everything is set up and running, you should be able to access:

- The admin panel at `http://admin.aliislamic.org`
- The party client at `http://party.aliislamic.org`

This setup will route requests to the appropriate endpoints in your Flask application using Nginx as a reverse proxy.