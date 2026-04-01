FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . /app

# Expose the standard huggingface spaces port
EXPOSE 7860

# Entry point using uvicorn as requested (Note: OpenEnv wraps the class into an ASGI app)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
