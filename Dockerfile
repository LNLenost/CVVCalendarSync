# Use the official Python image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy files into the container
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install cron
RUN apt-get update && apt-get install -y cron && rm -rf /var/lib/apt/lists/*

# Add the cron job
COPY cronjob /etc/cron.d/classeviva-cron

# Apply permissions to the cron job
RUN chmod 0644 /etc/cron.d/classeviva-cron

# Apply the cron job to the crontab
RUN crontab /etc/cron.d/classeviva-cron

# Make the script executable
RUN chmod +x ./classevivaSync.py

# Run the script
RUN python ./classevivaSync.py

# Command to run cron in the foreground
CMD ["cron", "-f"]
