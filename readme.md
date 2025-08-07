# AI Finance Chatbot for WhatsApp

An AI-powered WhatsApp chatbot that answers finance-related queries using OpenAI's function calling and tool integrations. Built with FastAPI, Twilio, LangChain-style prompt workflows, and PostgreSQL — deployed on Render.com.

---

## 🧠 Features

- ✅ Answers finance-related questions via WhatsApp using OpenAI responses
- ✅ Detects intent (stock/market queries) and triggers real-time web search tool
- ✅ Stores full chat history in PostgreSQL via SQLAlchemy ORM
- ✅ Handles multi-part message delivery with auto-chunking
- ✅ Formats AI responses for clean, readable WhatsApp rendering
- ✅ Runs on FastAPI with Twilio WhatsApp integration
- ✅ Logging, error handling, retry logic, and user state tracking via `response_id`
- ✅ Fully deployed and live on Render (API + DB)

---

## 🛠️ Tech Stack

- **FastAPI** – Backend API framework  
- **OpenAI SDK** – Language + tool-calling responses  
- **Twilio SDK** – WhatsApp integration  
- **SQLAlchemy + PostgreSQL** – Persistent message logging  
- **Alembic** – DB migrations  
- **Render.com** – Prod deployment for API + DB  
- **python-decouple** – Secure environment configuration  

---

## ⚙️ Installation

### 🧱 Prerequisites

- Python 3.9+
- A [Twilio](https://www.twilio.com/) account with WhatsApp sandbox access
- An [OpenAI](https://platform.openai.com/) API key
- A PostgreSQL instance (local or cloud-hosted)
- (Optional) Ngrok for local webhook testing

### 🧪 Local Setup

1. **Clone the repo**

```bash
git clone https://github.com/nawazkhan/ai-finance-chatbot.git
cd ai-finance-chatbot
```

2. **Create a .env file**
# OpenAI
OPENAI_API_KEY=your-openai-key
OPENAI_MODEL=text-completion-model-id

# Twilio
TWILIO_ACCOUNT_SID=your-sid
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_NUMBER=whatsapp:+14155238886  # or your sandbox/test number

# PostgreSQL
DB_DRIVER=postgresql
DB_USER=your_user
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=your_db

3. **	Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Run database migrations**
```bash
alembic upgrade head
```

5. **Start the server**
```bash
uvicorn main:app --reload
```
