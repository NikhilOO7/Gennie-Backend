#!/bin/bash

# Set variables
export PROJECT_ID="complete-stock-465308-m8"
export REGION="us-central1"
export SERVICE_ACCOUNT="ai-chatbot-voice-geenie@complete-stock-465308-m8.iam.gserviceaccount.com"

# Set project
gcloud config set project $PROJECT_ID

# Enable all required services
echo "Enabling required services..."
gcloud services enable compute.googleapis.com
gcloud services enable container.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable sqladmin.googleapis.com
gcloud services enable redis.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable servicenetworking.googleapis.com

# Create Cloud SQL with public IP (simpler approach)
echo "Creating Cloud SQL instance..."
gcloud sql instances create chatbot-postgres \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=$REGION \
  --assign-ip \
  --authorized-networks=0.0.0.0/0 \
  --root-password=admin123 \
  --database-flags=max_connections=100

# Wait for instance to be ready
echo "Waiting for Cloud SQL instance to be ready..."
gcloud sql operations wait --project=$PROJECT_ID \
  $(gcloud sql operations list --instance=chatbot-postgres --project=$PROJECT_ID --format="value(name)" --limit=1)

# Create database
echo "Creating database..."
gcloud sql databases create chatbot_db \
  --instance=chatbot-postgres

# Create user
echo "Creating database user..."
gcloud sql users create chatbot_user \
  --instance=chatbot-postgres \
  --password=your-secure-password

# Get connection details
echo "Getting connection details..."
export INSTANCE_CONNECTION_NAME=$(gcloud sql instances describe chatbot-postgres --format="value(connectionName)")
export INSTANCE_IP=$(gcloud sql instances describe chatbot-postgres --format="value(ipAddresses[0].ipAddress)")

echo "Cloud SQL Instance created successfully!"
echo "Connection Name: $INSTANCE_CONNECTION_NAME"
echo "Public IP: $INSTANCE_IP"

# Create Redis instance
echo "Creating Redis instance..."
gcloud redis instances create chatbot-redis \
  --size=1 \
  --region=$REGION \
  --redis-version=redis_7_0

# Get Redis host
export REDIS_HOST=$(gcloud redis instances describe chatbot-redis --region=$REGION --format="value(host)")
echo "Redis Host: $REDIS_HOST"

# Create secrets
echo "Creating secrets in Secret Manager..."
echo -n "1X0wNs9Emb9t9ZHXJhSWte27ehPKQuH9evbLROXAavU" | gcloud secrets create SECRET_KEY --data-file=-
echo -n "C5shPibGNe4IOtgFq9rPVeFRd7cr0gHrWxQ4MKGLnIU" | gcloud secrets create JWT_SECRET_KEY --data-file=-
echo -n "AIzaSyDu9kOB0qV-540miI85rMZShGjiFsae6eM" | gcloud secrets create GEMINI_API_KEY --data-file=-
echo -n "GmwemWrdiJGdtLz697sFAJsvl" | gcloud secrets create DB_PASSWORD --data-file=-

echo "Setup completed successfully!"
