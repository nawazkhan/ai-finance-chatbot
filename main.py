from openai import OpenAI
from fastapi import FastAPI, Form, Request, Depends
from decouple import config
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from models import Conversation, SessionLocal
from utils import send_whatsapp_message, logger

client = OpenAI(api_key=config('OPENAI_API_KEY'))

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
async def index():
    return {"msg": "working"}

@app.post("/message")
async def reply(request: Request, Body: str = Form(), db: Session = Depends(get_db)):
    logger.info("Webhook /message called")
    form_data = await request.form()
    logger.info(f"Form data received: {form_data}")
    whatsapp_number = form_data['From'].split('whatsapp:')[-1]
    logger.info(f"Sending the ChatGPT response to this number: {whatsapp_number}")

    input_messages = [
        {"role": "user", "content": Body},
        {"role": "system", "content": "You're a helpful investor, a serial founder and you've sold many startups. You understand nothing but business. You are here to give advice on business."}
    ]
    
    response = client.responses.create(
        model=config('OPENAI_MODEL'),
        input=input_messages,
        max_output_tokens=1000,
        temperature=0.5,
    )
    
    chatgpt_response = response.output_text
    
    try:
        conversation = Conversation(
            sender=whatsapp_number,
            message=Body,
            response=chatgpt_response
        )
        db.add(conversation)
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Failed to save conversation to database: {str(e)}")
    
    send_whatsapp_message(whatsapp_number, chatgpt_response)
    return {"message": chatgpt_response}
    
    
    
    


