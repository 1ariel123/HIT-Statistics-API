from fastapi import FastAPI
import os
from fastapi import FastAPI
from typing import Optional
from pydantic import BaseModel
from dotenv import load_dotenv
from pymongo import MongoClient

app = FastAPI()

load_dotenv()
uri = os.getenv("MONGODB_URI")
client = MongoClient(uri)

@app.get("/")
def read_root():
    return {"status": "Server is running", "message": "Ready for math and data!"}

@app.get("/health")
def health_check():
    # This helps Render know your app is alive
    return {"status": "healthy"}


class InstanceData(BaseModel):
    gradeDistributionAll: list
    gradeDistributionGroup: list
    instanceDescription: str

    #not needed
    midragKey: str
    #routeData: dict

class AssignmentData(BaseModel):
    instances: dict #list of InstanceData
    name: str

class CourseData(BaseModel):
    academicYear: str
    assignments: dict #list of AssignmentData
    courseIdentifierAndGroup: str
    finalGradeDistributionAll: list
    finalGradeDistributionGroup: list
    #finalGradeRoute: dict
    midragKey: str
    name: str
    semester: str




@app.post("/update-database")
def update_database(request: dict):
    return f"number of courses received: {len(request)}"

