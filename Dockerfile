# Use the official Python runtime image
FROM registry.cs.ui.ac.id/pkpl/base/python:3.13-slim  

# Create the app directory
RUN mkdir /app

# Set the working directory inside the container
WORKDIR /app

# Set environment variables 
# Prevents Python from writing pyc files to disk
ENV PYTHONDONTWRITEBYTECODE=1
# Prevents Python from buffering stdout and stderr
ENV PYTHONUNBUFFERED=1 

# Upgrade pip
RUN pip install --upgrade pip 

# Copy the Django project dependencies
COPY requirements.txt  /app/

# Install dependencies 
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Django project
COPY . /app/

# Expose the Django port
EXPOSE 8000

# Create a non-root user for security
RUN adduser --disabled-password --gecos "" appuser
RUN chown -R appuser:appuser /app
USER appuser

# Run migrations and start Gunicorn
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:8000 --workers 3 pharmori_be.wsgi:application"]
