# Use the official Python runtime image
FROM python:3.13  

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

# Run migrations, tests, and start the server
CMD ["sh", "-c", "python manage.py migrate && python manage.py test && python manage.py runserver 0.0.0.0:8000"]
