from fastapi import FastAPI
import os
from fastapi import FastAPI
from typing import Optional
from pydantic import BaseModel
from dotenv import load_dotenv
from pymongo import MongoClient
from fastapi.middleware.cors import CORSMiddleware


#1
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allows your extension to talk to the API
    allow_methods=["POST", "OPTIONS"], # Explicitly allow these
    allow_headers=["*"],
)


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
class updateDatabaseRequest(BaseModel):
    coursesData: dict #list of CourseData



@app.post("/update-database")
def update_database(request: updateDatabaseRequest):
    return f"number of courses received: {len(request.coursesData)}"

@app.get("/update-database")
def get_update_database():
    try:
        # The 'ping' command is cheap and does not require auth for most setups
        client.admin.command('ping')
        return {"message": "Pinged your deployment. You successfully connected to MongoDB!"}
    except Exception as e:
        #print(f"An error occurred: {e}")
        return {"message": "Failed to connect to MongoDB:", "error": str(e)}
    finally:
        #client.close()
        pass
