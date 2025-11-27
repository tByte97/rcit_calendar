from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

DB_URL = 'sqlite:///./advent.db'
engine = create_engine(DB_URL, connect_args={"check_same_thread": False })
Sessionlocal = sessionmaker(autocommit = False, autoflush= False, bind=engine)
Base = declarative_base()


class UserAttempt(Base):
    __tablename__ = 'attempts' 
    
    id = Column(Integer, primary_key=True, index=True)
    stud_email = Column(String, index=True)
    day = Column(Integer, index=True)
    timestamp = Column(DateTime, default=datetime.now)

    __table_args__ = (
        UniqueConstraint('stud_email', 'day', name='one_attempt_per_day'),
    )

class Winner(Base):
    __tablename__ = 'winners'
    
    id = Column(Integer, primary_key=True, index=True)
    day = Column(Integer, index=True)
    stud_email = Column(String)
    prize_name = Column(String)
    won_at = Column(DateTime, default=datetime.now)

Base.metadata.create_all(bind=engine)

def get_db():
    db = Sessionlocal()
    try:
        yield db
    finally:
        db.close()