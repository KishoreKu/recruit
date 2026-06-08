import os
import sys
import psycopg2

def migrate():
    print("Reading database credentials...")
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        print("Using DATABASE_URL from environment...")
        try:
            conn = psycopg2.connect(db_url)
        except Exception as e:
            print(f"❌ Connection with DATABASE_URL failed: {e}")
            sys.exit(1)
    else:
        print("Using default credentials...")
        try:
            conn = psycopg2.connect(
                host="westley-db-pg.postgres.database.azure.com",
                database="postgres",
                user="westleyadmin",
                password="P@ssw0rd_Westley_2026_Recruit",
                sslmode="require"
            )
        except Exception as e:
            print(f"❌ Connection with default credentials failed: {e}")
            sys.exit(1)
            
    try:
        conn.autocommit = True
        cursor = conn.cursor()
        
        schema_path = os.path.join(os.path.dirname(__file__), "schema_agents.sql")
        print(f"Reading schema from: {schema_path}...")
        with open(schema_path, "r") as f:
            sql = f.read()
            
        print("Executing SQL schema...")
        cursor.execute(sql)
        print("✅ Database migrations completed successfully!")
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    migrate()
