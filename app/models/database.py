from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base

SQLALCHEMY_DATABASE_URL = "sqlite:///./phishing_simulator.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class PhishingTarget(Base):
    __tablename__ = "phishing_targets"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True)
    token = Column(String, unique=True, index=True)
    is_sent = Column(Boolean, default=True)
    is_opened = Column(Boolean, default=False)
    is_clicked = Column(Boolean, default=False)
    is_compromised = Column(Boolean, default=False)