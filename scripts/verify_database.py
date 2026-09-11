#!/usr/bin/env python3
"""Verify the database has 15 menu items with embeddings."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from google.cloud.sql.connector import Connector
import pg8000

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# Verify required environment variables
required_vars = ['GOOGLE_CLOUD_PROJECT', 'REGION', 'DB_PASSWORD', 'DB_INSTANCE', 'DB_NAME']
missing_vars = [var for var in required_vars if not os.environ.get(var)]

if missing_vars:
    print(f"ERROR: Missing environment variables: {', '.join(missing_vars)}", file=sys.stderr)
    sys.exit(1)


def verify_database():
    """Check that 15 menu items exist with embeddings."""
    connector = Connector()

    try:
        project = os.environ['GOOGLE_CLOUD_PROJECT']
        region = os.environ['REGION']
        password = os.environ['DB_PASSWORD']
        instance = os.environ['DB_INSTANCE']
        database = os.environ['DB_NAME']

        conn = connector.connect(
            f"{project}:{region}:{instance}",
            "pg8000",
            user="postgres",
            password=password,
            db=database
        )
        cursor = conn.cursor()

        # Count menu items and embeddings
        cursor.execute("SELECT COUNT(*) FROM menu_items")
        item_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM menu_items WHERE description_embedding IS NOT NULL")
        embedding_count = cursor.fetchone()[0]

        print(f"Menu Items: {item_count}/15")
        print(f"Embeddings: {embedding_count}/15")

        cursor.close()
        conn.close()

        if item_count == 15 and embedding_count == 15:
            print("\n✓ Database ready!")
            return True
        else:
            print("\n✗ Database not ready")
            return False

    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        return False
    finally:
        connector.close()


if __name__ == "__main__":
    success = verify_database()
    sys.exit(0 if success else 1)