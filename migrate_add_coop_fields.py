"""
Migration script to add cooperative operation fields to production_schedule table
"""
from sqlalchemy import text
from config import DATABASE_URL
from sqlalchemy import create_engine

def migrate():
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        # Check if columns already exist
        result = conn.execute(text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'production_schedule' AND column_name = 'is_cooperation'
        """))
        if result.fetchone():
            print("Column is_cooperation already exists, skipping...")
        else:
            # Add is_cooperation column
            conn.execute(text("""
                ALTER TABLE production_schedule 
                ADD COLUMN is_cooperation BOOLEAN DEFAULT FALSE
            """))
            print("Added is_cooperation column")
        
        result = conn.execute(text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'production_schedule' AND column_name = 'coop_company_name'
        """))
        if result.fetchone():
            print("Column coop_company_name already exists, skipping...")
        else:
            # Add coop_company_name column
            conn.execute(text("""
                ALTER TABLE production_schedule 
                ADD COLUMN coop_company_name VARCHAR(255)
            """))
            print("Added coop_company_name column")
        
        result = conn.execute(text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'production_schedule' AND column_name = 'coop_duration_days'
        """))
        if result.fetchone():
            print("Column coop_duration_days already exists, skipping...")
        else:
            # Add coop_duration_days column
            conn.execute(text("""
                ALTER TABLE production_schedule 
                ADD COLUMN coop_duration_days INTEGER
            """))
            print("Added coop_duration_days column")
        
        conn.commit()
        print("Migration completed successfully!")

if __name__ == "__main__":
    migrate()
