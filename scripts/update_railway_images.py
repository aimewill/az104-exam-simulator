#!/usr/bin/env python3
"""Update exhibit_image paths in Railway PostgreSQL to match new filenames."""

import sys
import os
from pathlib import Path

# Get Railway PostgreSQL URL from command line
if len(sys.argv) < 2:
    print("Usage: python update_railway_images.py <RAILWAY_POSTGRES_URL>")
    sys.exit(1)

RAILWAY_URL = sys.argv[1]

# Connect to Railway PostgreSQL
from sqlalchemy import create_engine, text

engine = create_engine(RAILWAY_URL)

# Get mapping from local SQLite
sys.path.insert(0, str(Path(__file__).parent.parent))
from backend.app.database import SessionLocal
from backend.app.models import Question

local_db = SessionLocal()
local_questions = local_db.query(Question).filter(Question.exhibit_image.isnot(None)).all()

print(f"Found {len(local_questions)} questions with images in local DB")

# Update Railway
with engine.connect() as conn:
    updated = 0
    for q in local_questions:
        # Update by stable_id to match questions across databases
        result = conn.execute(
            text("UPDATE questions SET exhibit_image = :img WHERE stable_id = :sid"),
            {"img": q.exhibit_image, "sid": q.stable_id}
        )
        if result.rowcount > 0:
            updated += 1
    conn.commit()
    print(f"Updated {updated} questions in Railway PostgreSQL")

local_db.close()
print("Done!")
