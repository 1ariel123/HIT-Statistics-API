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


@app.get("/math")
def perform_math_get():
    return {"message": "Please use POST method to perform math operations."}


class InstanceData(BaseModel):
    gradeDistributionAll: list
    gradeDistributionGroup: list
    instanceDescription: str

    #not needed
    midragKey: str
    routeData: dict

class AssignmentData(BaseModel):
    instances: dict #list of InstanceData
    name: str

class CourseData(BaseModel):
    academicYear: str
    assignments: dict #list of AssignmentData
    courseIdentifierAndGroup: str
    finalGradeDistributionAll: list
    finalGradeDistributionGroup: list
    finalGradeRoute: dict
    midragKey: str
    name: str
    semester: str

class DatabaseUpdateRequest(BaseModel):
    coursesData: dict #list of CourseData


@app.post("/update-database")
def update_database(request: DatabaseUpdateRequest):
    return request.coursesData["course_0"]

