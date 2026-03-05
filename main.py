from fastapi import FastAPI
import os
from fastapi import FastAPI
from typing import Optional
from pydantic import BaseModel

app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "Server is running", "message": "Ready for math and data!"}

@app.get("/health")
def health_check():
    # This helps Render know your app is alive
    return {"status": "healthy"}



# Define what the JSON should look like
class MathRequest(BaseModel):
    num1: float
    num2: float
    operation: str

@app.post("/math")
def perform_math(request: MathRequest):
    # Access data using dot notation
    a = request.num1
    b = request.num2
    op = request.operation

    if op == "add":
        result = a + b
    elif op == "multiply":
        result = a * b
    else:
        return {"error": "Unsupported operation"}

    return {"result": result}

