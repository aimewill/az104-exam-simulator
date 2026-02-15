#!/bin/bash
# Reset AZ-104 Exam Simulator - Clear all session history and progress

DB_PATH="$HOME/Projects/Az104app/data/az104.db"

if [ ! -f "$DB_PATH" ]; then
    echo "❌ Database not found at $DB_PATH"
    exit 1
fi

echo "🔄 Clearing exam sessions and progress..."
sqlite3 "$DB_PATH" "DELETE FROM exam_sessions; DELETE FROM domain_stats;"

echo "✅ Reset complete!"
echo "   - All exam sessions cleared"
echo "   - Domain statistics reset"
echo "   - Questions preserved (667)"
