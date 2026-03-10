from fastapi import FastAPI
from app.schemas import Question
from app.ai_engine import ask_ai

app = FastAPI(title="AI Service")

@app.post("/ask")
def ask(question: Question):
    answer = ask_ai(question.question)
    return {"answer": answer}
