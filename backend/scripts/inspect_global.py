import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    rows = db.execute(text("SELECT id, location, city, country FROM jobs WHERE city = 'Nashville' LIMIT 3")).all()
    for r in rows:
        print(r)
finally:
    db.close()
