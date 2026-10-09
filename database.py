from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Database se connection ka address
# postgres:password mein apna naya password daalo!
DATABASE_URL = "postgresql+psycopg://postgres:skyguard123@localhost:5432/skyguard_db"

# Engine = database se baat karne wala "engine"
engine = create_engine(DATABASE_URL)

# Session = har baar database se baat karne ka ek "connection"
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base = isse hamari tables (models) banengi
Base = declarative_base()

# Ye function har request ko ek database session deta hai
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()