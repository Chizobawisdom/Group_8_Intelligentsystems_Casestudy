# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory inside the container
WORKDIR /app

# Copy requirements first (for Docker caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
COPY . .

# Command to run your app (adjust based on your framework)
# Example for Streamlit:
CMD ["streamlit", "run", "src/main.py"]
# Example for FastAPI:
# CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]