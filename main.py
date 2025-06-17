from openai import OpenAI
from fastapi import FastAPI, Form, Request, Depends
from decouple import config
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime, timedelta
from typing import Optional

from models import (
    Conversation, SessionLocal, User, UserRole, Patient, Physiotherapist, 
    Appointment, ExerciseLog, DailyWorkflow, AppointmentStatus
)
from utils import send_whatsapp_message, logger

client = OpenAI(api_key=config('OPENAI_API_KEY'))
app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_or_create_user(phone_number: str, db: Session) -> User:
    user = db.query(User).filter(User.phone_number == phone_number).first()
    if not user:
        user = User(phone_number=phone_number)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

def detect_user_role(message: str) -> Optional[str]:
    patient_keywords = ['patient', 'appointment', 'exercise', 'pain', 'therapy', 'treatment', 'hurt', 'injured']
    physio_keywords = ['physiotherapist', 'therapist', 'doctor', 'pt', 'assessment', 'diagnos', 'treat']
    
    message_lower = message.lower()
    
    if any(keyword in message_lower for keyword in patient_keywords):
        return "patient"
    elif any(keyword in message_lower for keyword in physio_keywords):
        return "physiotherapist"
    return None

class PatientAgent:
    def __init__(self, user: User, db: Session):
        self.user = user
        self.db = db
        self.patient = user.patient_profile
        
    def get_system_prompt(self) -> str:
        return """You are a helpful physiotherapy assistant for patients. Your role is to:
        1. Help patients schedule and manage appointments
        2. Guide them through prescribed exercises
        3. Track their progress and pain levels
        4. Provide encouragement and support
        5. Answer questions about their treatment plan
        6. Remind them about daily exercises and check-ins
        
        Always be empathetic, supportive, and professional. If medical advice is needed beyond your scope, 
        recommend consulting with their physiotherapist directly."""
    
    def handle_message(self, message: str) -> str:
        message_lower = message.lower()
        
        if any(word in message_lower for word in ['schedule', 'appointment', 'book']):
            return self._handle_appointment_request(message)
        elif any(word in message_lower for word in ['exercise', 'workout', 'log']):
            return self._handle_exercise_logging(message)
        elif any(word in message_lower for word in ['pain', 'hurt', 'progress']):
            return self._handle_progress_check(message)
        else:
            return self._general_patient_response(message)
    
    def _handle_appointment_request(self, message: str) -> str:
        if not self.patient:
            return "I'd be happy to help you schedule an appointment! First, let me set up your patient profile. What condition are you receiving treatment for?"
        
        upcoming_appointments = self.db.query(Appointment)\
            .filter(Appointment.patient_id == self.patient.id)\
            .filter(Appointment.scheduled_date > datetime.utcnow())\
            .filter(Appointment.status == AppointmentStatus.SCHEDULED)\
            .order_by(Appointment.scheduled_date)\
            .limit(3).all()
        
        if upcoming_appointments:
            apt_list = "\n".join([f"• {apt.scheduled_date.strftime('%Y-%m-%d %H:%M')}" for apt in upcoming_appointments])
            return f"Here are your upcoming appointments:\n{apt_list}\n\nWould you like to schedule another appointment or modify an existing one?"
        else:
            return "I can help you schedule an appointment with your physiotherapist. What days and times work best for you?"
    
    def _handle_exercise_logging(self, message: str) -> str:
        return "Great! Let's log your exercise session. Please tell me:\n• Exercise name\n• Number of sets and reps\n• Pain level (1-10)\n• Any notes about how it felt"
    
    def _handle_progress_check(self, message: str) -> str:
        if not self.patient:
            return "I'd love to help track your progress! Let me first set up your patient profile."
        
        recent_logs = self.db.query(ExerciseLog)\
            .filter(ExerciseLog.patient_id == self.patient.id)\
            .filter(ExerciseLog.logged_at > datetime.utcnow() - timedelta(days=7))\
            .order_by(desc(ExerciseLog.logged_at))\
            .limit(5).all()
        
        if recent_logs:
            avg_pain = sum(log.pain_level for log in recent_logs) / len(recent_logs)
            return f"Here's your recent progress:\n• {len(recent_logs)} exercise sessions this week\n• Average pain level: {avg_pain:.1f}/10\n\nHow are you feeling today compared to last week?"
        else:
            return "I don't see any recent exercise logs. How has your pain level been lately on a scale of 1-10?"
    
    def _general_patient_response(self, message: str) -> str:
        return self._get_ai_response(message, "patient_agent")
    
    def _get_ai_response(self, message: str, agent_type: str) -> str:
        api_params = {
            "model": config('OPENAI_MODEL'),
            "input": f"System: {self.get_system_prompt()}\n\nPatient: {message}",
            "max_output_tokens": 1000,
            "temperature": 0.7,
        }
        response = client.responses.create(**api_params)
        return response.output_text

class PhysiotherapistAgent:
    def __init__(self, user: User, db: Session):
        self.user = user
        self.db = db
        self.physiotherapist = user.physiotherapist_profile
        
    def get_system_prompt(self) -> str:
        return """You are a professional physiotherapy practice management assistant. Your role is to:
        1. Help physiotherapists manage their patient caseload
        2. Provide treatment plan suggestions and exercise recommendations
        3. Track patient progress and outcomes
        4. Schedule and manage appointments
        5. Generate reports and assessments
        6. Assist with clinical documentation
        
        Always maintain professional standards and remind that final clinical decisions rest with the licensed physiotherapist."""
    
    def handle_message(self, message: str) -> str:
        message_lower = message.lower()
        
        if any(word in message_lower for word in ['patient', 'caseload', 'list']):
            return self._handle_patient_management(message)
        elif any(word in message_lower for word in ['appointment', 'schedule', 'calendar']):
            return self._handle_appointment_management(message)
        elif any(word in message_lower for word in ['progress', 'report', 'assessment']):
            return self._handle_progress_reports(message)
        else:
            return self._general_physio_response(message)
    
    def _handle_patient_management(self, message: str) -> str:
        if not self.physiotherapist:
            return "Welcome! Let me set up your physiotherapist profile. Please provide your license number and specialization."
        
        patients = self.db.query(Patient)\
            .filter(Patient.physiotherapist_id == self.physiotherapist.id)\
            .limit(10).all()
        
        if patients:
            patient_list = "\n".join([f"• {patient.user.name or patient.user.phone_number} - {patient.condition}" for patient in patients])
            return f"Here are your patients:\n{patient_list}\n\nWould you like details on any specific patient?"
        else:
            return "You don't have any patients assigned yet. Would you like to add a new patient to your caseload?"
    
    def _handle_appointment_management(self, message: str) -> str:
        today = datetime.utcnow().date()
        appointments = self.db.query(Appointment)\
            .filter(Appointment.physiotherapist_id == self.physiotherapist.id)\
            .filter(Appointment.scheduled_date >= today)\
            .order_by(Appointment.scheduled_date)\
            .limit(5).all()
        
        if appointments:
            apt_list = "\n".join([f"• {apt.scheduled_date.strftime('%Y-%m-%d %H:%M')} - {apt.patient.user.name or apt.patient.user.phone_number}" for apt in appointments])
            return f"Your upcoming appointments:\n{apt_list}\n\nWould you like to modify any appointments or schedule new ones?"
        else:
            return "You have no upcoming appointments scheduled. Would you like to schedule appointments for your patients?"
    
    def _handle_progress_reports(self, message: str) -> str:
        return "I can help generate progress reports for your patients. Which patient would you like a report for?"
    
    def _general_physio_response(self, message: str) -> str:
        return self._get_ai_response(message, "physiotherapist_agent")
    
    def _get_ai_response(self, message: str, agent_type: str) -> str:
        api_params = {
            "model": config('OPENAI_MODEL'),
            "input": f"System: {self.get_system_prompt()}\n\nPhysiotherapist: {message}",
            "max_output_tokens": 1000,
            "temperature": 0.7,
        }
        response = client.responses.create(**api_params)
        return response.output_text

class WorkflowManager:
    def __init__(self, db: Session):
        self.db = db
    
    def schedule_daily_workflows(self, user: User):
        if user.role == UserRole.PATIENT:
            self._schedule_patient_workflows(user)
        elif user.role == UserRole.PHYSIOTHERAPIST:
            self._schedule_physio_workflows(user)
    
    def _schedule_patient_workflows(self, user: User):
        tomorrow = datetime.utcnow() + timedelta(days=1)
        morning_check = tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
        evening_reminder = tomorrow.replace(hour=19, minute=0, second=0, microsecond=0)
        
        workflows = [
            DailyWorkflow(user_id=user.id, workflow_type="morning_check", scheduled_time=morning_check),
            DailyWorkflow(user_id=user.id, workflow_type="exercise_reminder", scheduled_time=evening_reminder)
        ]
        
        for workflow in workflows:
            self.db.add(workflow)
        self.db.commit()
    
    def _schedule_physio_workflows(self, user: User):
        tomorrow = datetime.utcnow() + timedelta(days=1)
        daily_summary = tomorrow.replace(hour=8, minute=0, second=0, microsecond=0)
        
        workflow = DailyWorkflow(
            user_id=user.id, 
            workflow_type="daily_summary", 
            scheduled_time=daily_summary
        )
        self.db.add(workflow)
        self.db.commit()

@app.get("/")
async def index():
    return {"msg": "Physiotherapy Multi-Agent Workflow System - Active"}

@app.post("/message")
async def reply(request: Request, Body: str = Form(), db: Session = Depends(get_db)):
    logger.info("Webhook /message called")
    form_data = await request.form()
    whatsapp_number = form_data['From'].split('whatsapp:')[-1]
    
    user = get_or_create_user(whatsapp_number, db)
    workflow_manager = WorkflowManager(db)
    
    if not user.role:
        detected_role = detect_user_role(Body)
        if detected_role:
            user.role = UserRole.PATIENT if detected_role == "patient" else UserRole.PHYSIOTHERAPIST
            db.commit()
            workflow_manager.schedule_daily_workflows(user)
            
            welcome_msg = f"Welcome! I've identified you as a {detected_role}. "
            if detected_role == "patient":
                welcome_msg += "I'm here to help with your physiotherapy journey - scheduling appointments, tracking exercises, and monitoring your progress."
            else:
                welcome_msg += "I'm here to help manage your practice - patient caseloads, appointments, and progress tracking."
            
            send_whatsapp_message(whatsapp_number, welcome_msg)
        else:
            send_whatsapp_message(whatsapp_number, "Hello! I'm your physiotherapy assistant. Are you a patient seeking treatment or a physiotherapist managing your practice?")
            return {"message": "Role identification needed"}
    
    if user.role == UserRole.PATIENT:
        agent = PatientAgent(user, db)
        agent_type = "patient_agent"
    else:
        agent = PhysiotherapistAgent(user, db)
        agent_type = "physiotherapist_agent"
    
    response_text = agent.handle_message(Body)
    
    try:
        conversation = Conversation(
            user_id=user.id,
            sender=whatsapp_number,
            message=Body,
            response=response_text,
            agent_type=agent_type,
            created_at=datetime.utcnow()
        )
        db.add(conversation)
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Failed to save conversation: {str(e)}")
    
    send_whatsapp_message(whatsapp_number, response_text)
    return {"message": response_text}

@app.post("/daily-workflow")
async def trigger_daily_workflows(db: Session = Depends(get_db)):
    current_time = datetime.utcnow()
    pending_workflows = db.query(DailyWorkflow)\
        .filter(DailyWorkflow.scheduled_time <= current_time)\
        .filter(DailyWorkflow.completed == False)\
        .all()
    
    for workflow in pending_workflows:
        user = db.query(User).filter(User.id == workflow.user_id).first()
        if not user:
            continue
            
        if workflow.workflow_type == "morning_check":
            message = "Good morning! How are you feeling today? Any pain or stiffness? Don't forget your morning exercises!"
        elif workflow.workflow_type == "exercise_reminder":
            message = "Evening reminder: Have you completed your prescribed exercises today? Remember to log your session!"
        elif workflow.workflow_type == "daily_summary":
            message = "Daily Summary: Check your patient progress, upcoming appointments, and any action items for today."
        else:
            continue
            
        send_whatsapp_message(user.phone_number, message)
        workflow.completed = True
    
    db.commit()
    return {"processed": len(pending_workflows)}    


