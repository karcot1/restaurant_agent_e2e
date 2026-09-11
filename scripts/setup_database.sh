#!/bin/bash
set -e
source .env

# echo "================================================"
# echo "Database Setup"
# echo "================================================"
# echo ""

# # Step 1: Create Cloud SQL instance
# echo "[1/5] Creating Cloud SQL instance..."

# # Check if instance already exists
# if gcloud sql instances describe "$DB_INSTANCE" --quiet >/dev/null 2>&1; then
#     echo "      Instance already exists"
# else
#     echo "      Creating instance (takes 5-10 minutes)..."
#     gcloud sql instances create "$DB_INSTANCE" \
#         --database-version=POSTGRES_17 \
#         --tier=db-custom-1-3840 \
#         --edition=ENTERPRISE \
#         --region="$REGION" \
#         --root-password="$DB_PASSWORD" \
#         --enable-google-ml-integration \
#         --database-flags cloudsql.enable_google_ml_integration=on \
#         --quiet
# fi
# echo "      ✓ Instance ready"
# echo ""

# # Step 2: Verify instance is ready
# echo "[2/5] Verifying instance state..."

# STATE=$(gcloud sql instances describe "$DB_INSTANCE" --format='value(state)')

# if [ "$STATE" != "RUNNABLE" ]; then
#     echo "ERROR: Instance not ready (state: $STATE)"
#     exit 1
# fi
# echo "      ✓ Instance is RUNNABLE"
# echo ""

# # Step 3: Grant IAM permissions
# echo "[3/5] Granting Vertex AI permissions..."

# SERVICE_ACCOUNT=$(gcloud sql instances describe "$DB_INSTANCE" \
#     --format='value(serviceAccountEmailAddress)')

# if [ -z "$SERVICE_ACCOUNT" ]; then
#     echo "ERROR: Could not retrieve service account"
#     exit 1
# fi

# gcloud projects add-iam-policy-binding "$GOOGLE_CLOUD_PROJECT" \
#     --member="serviceAccount:$SERVICE_ACCOUNT" \
#     --role="roles/aiplatform.user" \
#     --quiet

# echo "      ✓ Permissions granted"
# echo ""

# # Step 4: Create database
# echo "[4/5] Creating database..."

# # Check if database already exists
# if gcloud sql databases describe "$DB_NAME" \
#     --instance="$DB_INSTANCE" --quiet >/dev/null 2>&1; then
#     echo "      Database already exists"
# else
#     gcloud sql databases create "$DB_NAME" \
#         --instance="$DB_INSTANCE" \
#         --quiet
# fi

# echo "      ✓ Database '$DB_NAME' ready"
# echo ""

# Step 5: Seed database and generate embeddings
echo "[5/5] Seeding database and generating embeddings..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SETUP_SCRIPT="${SCRIPT_DIR}/setup_restaurant_db.py"

if [ ! -f "$SETUP_SCRIPT" ]; then
    echo "ERROR: Setup script not found: $SETUP_SCRIPT"
    exit 1
fi

uv run "$SETUP_SCRIPT"

echo ""
echo "================================================"
echo "Setup complete!"
echo "================================================"
echo ""