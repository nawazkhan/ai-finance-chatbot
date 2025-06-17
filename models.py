from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, ForeignKey, Boolean, Enum
from sqlalchemy.engine import URL
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from decouple import config
from datetime import datetime
import enum

url = URL.create(
    drivername=config('DB_DRIVER'),
    username=config('DB_USER'),
    password=config('DB_PASSWORD'),
    host=config('DB_HOST'),
    port=config('DB_PORT'),
    database=config('DB_NAME')
)

engine = create_engine(url)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class UserRole(enum.Enum):
    PATIENT = "patient"
    PHYSIOTHERAPIST = "physiotherapist"

class AppointmentStatus(enum.Enum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String, unique=True, index=True)
    role = Column(Enum(UserRole))
    name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    conversations = relationship("Conversation", back_populates="user")
    patient_profile = relationship("Patient", back_populates="user", uselist=False)
    physiotherapist_profile = relationship("Physiotherapist", back_populates="user", uselist=False)

class Patient(Base):
    __tablename__ = "patients"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    physiotherapist_id = Column(Integer, ForeignKey("physiotherapists.id"))
    condition = Column(String)
    treatment_goals = Column(Text)
    
    user = relationship("User", back_populates="patient_profile")
    physiotherapist = relationship("Physiotherapist", back_populates="patients")
    appointments = relationship("Appointment", back_populates="patient")
    exercise_logs = relationship("ExerciseLog", back_populates="patient")

class Physiotherapist(Base):
    __tablename__ = "physiotherapists"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    license_number = Column(String)
    specialization = Column(String)
    
    user = relationship("User", back_populates="physiotherapist_profile")
    patients = relationship("Patient", back_populates="physiotherapist")
    appointments = relationship("Appointment", back_populates="physiotherapist")

class Appointment(Base):
    __tablename__ = "appointments"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    physiotherapist_id = Column(Integer, ForeignKey("physiotherapists.id"))
    scheduled_date = Column(DateTime)
    status = Column(Enum(AppointmentStatus), default=AppointmentStatus.SCHEDULED)
    notes = Column(Text)
    
    patient = relationship("Patient", back_populates="appointments")
    physiotherapist = relationship("Physiotherapist", back_populates="appointments")

class ExerciseLog(Base):
    __tablename__ = "exercise_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    exercise_name = Column(String)
    sets = Column(Integer)
    reps = Column(Integer)
    pain_level = Column(Integer)  # 1-10 scale
    notes = Column(Text)
    logged_at = Column(DateTime, default=datetime.utcnow)
    
    patient = relationship("Patient", back_populates="exercise_logs")

class DailyWorkflow(Base):
    __tablename__ = "daily_workflows"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    workflow_type = Column(String)  # "morning_check", "exercise_reminder", "progress_update"
    scheduled_time = Column(DateTime)
    completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    sender = Column(String)  # phone number for backward compatibility
    message = Column(String)
    response = Column(String)
    response_id = Column(String, nullable=True)
    agent_type = Column(String)  # "patient_agent" or "physiotherapist_agent"
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="conversations")

Base.metadata.create_all(engine)
