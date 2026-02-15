#!/usr/bin/env python3
"""Migrate questions from local SQLite to Railway PostgreSQL."""
import os
import sys
import json
import sqlite3

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Local SQLite database
LOCAL_DB = os.path.join(os.path.dirname(__file__), '..', 'data', 'az104.db')

def migrate(postgres_url: str):
    """Migrate data from local SQLite to PostgreSQL."""
    print(f"Connecting to local SQLite: {LOCAL_DB}")
    
    # Connect to local SQLite
    sqlite_conn = sqlite3.connect(LOCAL_DB)
    sqlite_conn.row_factory = sqlite3.Row
    
    # Connect to PostgreSQL
    print(f"Connecting to PostgreSQL...")
    pg_engine = create_engine(postgres_url)
    
    # Create tables in PostgreSQL
    print("Creating tables...")
    with pg_engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                display_name VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS questions (
                id SERIAL PRIMARY KEY,
                stable_id VARCHAR(64) UNIQUE,
                text TEXT NOT NULL,
                choices JSON NOT NULL,
                correct_answers JSON NOT NULL,
                explanation TEXT,
                question_type VARCHAR(20) DEFAULT 'single',
                domain_id VARCHAR(50),
                source_file VARCHAR(255),
                source_page INTEGER,
                exhibit_image VARCHAR(255),
                series_id VARCHAR(64),
                sequence_number INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                times_shown INTEGER DEFAULT 0,
                times_correct INTEGER DEFAULT 0
            )
        """))
        
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS exam_sessions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                mode VARCHAR(30) NOT NULL,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                time_limit_minutes INTEGER,
                paused_at TIMESTAMP,
                total_paused_seconds INTEGER DEFAULT 0,
                total_questions INTEGER DEFAULT 60,
                correct_count INTEGER,
                percent_score FLOAT,
                scaled_score INTEGER,
                passed BOOLEAN,
                question_ids JSON NOT NULL,
                answers JSON DEFAULT '{}'
            )
        """))
        
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS domain_stats (
                id SERIAL PRIMARY KEY,
                domain_id VARCHAR(50) UNIQUE,
                domain_name VARCHAR(100) NOT NULL,
                total_questions INTEGER DEFAULT 0,
                total_shown INTEGER DEFAULT 0,
                total_correct INTEGER DEFAULT 0
            )
        """))
        
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS import_records (
                id SERIAL PRIMARY KEY,
                filename VARCHAR(255) NOT NULL,
                file_hash VARCHAR(64) NOT NULL,
                imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                questions_imported INTEGER DEFAULT 0,
                status VARCHAR(20) DEFAULT 'pending'
            )
        """))
        
        # Create indexes
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_questions_stable_id ON questions(stable_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_questions_domain_id ON questions(domain_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_questions_series_id ON questions(series_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_exam_sessions_user_id ON exam_sessions(user_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_users_email ON users(email)"))
        
        conn.commit()
    
    # Migrate questions
    print("Migrating questions...")
    cursor = sqlite_conn.execute("SELECT * FROM questions")
    questions = cursor.fetchall()
    
    with pg_engine.connect() as conn:
        # Clear existing questions
        conn.execute(text("DELETE FROM questions"))
        
        for q in questions:
            conn.execute(text("""
                INSERT INTO questions (
                    stable_id, text, choices, correct_answers, explanation,
                    question_type, domain_id, source_file, source_page,
                    exhibit_image, series_id, sequence_number,
                    times_shown, times_correct
                ) VALUES (
                    :stable_id, :text, :choices, :correct_answers, :explanation,
                    :question_type, :domain_id, :source_file, :source_page,
                    :exhibit_image, :series_id, :sequence_number,
                    :times_shown, :times_correct
                )
            """), {
                'stable_id': q['stable_id'],
                'text': q['text'],
                'choices': q['choices'] if isinstance(q['choices'], str) else json.dumps(q['choices']),
                'correct_answers': q['correct_answers'] if isinstance(q['correct_answers'], str) else json.dumps(q['correct_answers']),
                'explanation': q['explanation'],
                'question_type': q['question_type'],
                'domain_id': q['domain_id'],
                'source_file': q['source_file'],
                'source_page': q['source_page'],
                'exhibit_image': q['exhibit_image'],
                'series_id': q['series_id'],
                'sequence_number': q['sequence_number'],
                'times_shown': q['times_shown'] or 0,
                'times_correct': q['times_correct'] or 0,
            })
        
        conn.commit()
    
    print(f"✅ Migrated {len(questions)} questions!")
    
    # Migrate domain stats
    print("Migrating domain stats...")
    cursor = sqlite_conn.execute("SELECT * FROM domain_stats")
    stats = cursor.fetchall()
    
    with pg_engine.connect() as conn:
        conn.execute(text("DELETE FROM domain_stats"))
        
        for s in stats:
            conn.execute(text("""
                INSERT INTO domain_stats (domain_id, domain_name, total_questions, total_shown, total_correct)
                VALUES (:domain_id, :domain_name, :total_questions, :total_shown, :total_correct)
            """), {
                'domain_id': s['domain_id'],
                'domain_name': s['domain_name'],
                'total_questions': s['total_questions'] or 0,
                'total_shown': s['total_shown'] or 0,
                'total_correct': s['total_correct'] or 0,
            })
        
        conn.commit()
    
    print(f"✅ Migrated {len(stats)} domain stats!")
    
    sqlite_conn.close()
    print("\n🎉 Migration complete!")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python migrate_to_railway.py <POSTGRES_URL>")
        print("\nGet the URL with: railway link (select Postgres) && railway variables | grep DATABASE_URL")
        sys.exit(1)
    
    postgres_url = sys.argv[1]
    migrate(postgres_url)
