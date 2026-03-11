from datetime import datetime, timedelta, timezone
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
    gradeDistributionAll: list | None = None
    gradeDistributionGroup: list | None = None
    instanceDescription: str

    #not needed
    midragKey: str | None = None
    #routeData: dict

class AssignmentData(BaseModel):
    instances: dict #list of InstanceData
    name: str

class CourseData(BaseModel):
    academicYear: str
    assignments: dict #list of AssignmentData
    courseIdentifierAndGroup: str
    finalGradeDistributionAll: list | None = None
    finalGradeDistributionGroup: list | None = None
    #finalGradeRoute: dict
    midragKey: str | None = None
    name: str
    semester: str
    lecturer: str | None = None
class updateDatabaseRequest(BaseModel):
    coursesData: dict #list of CourseData
    logEntry: dict




@app.get("/ping-database")
def ping_database():
    try:
        client.admin.command('ping')
        return {"message": "Pinged your deployment. You successfully connected to MongoDB!"}
    except Exception as e:
        return {"message": "Failed to connect to MongoDB:", "error": str(e)}
    

def academicYearToNumber(academicYear: str) -> int:
    # input: תשפו
    # output: 5786
    academicYearDict={"א": 1, "ב": 2, "ג": 3, "ד": 4, "ה": 5, "ו": 6, "ז": 7, "ח": 8, "ט": 9, "י": 10, "כ": 20, "ל": 30, "מ": 40, "נ": 50, "ס": 60, "ע": 70, "פ": 80, "צ": 90, "ק": 100, "ר": 200, "ש": 300, "ת": 400}
    NumericYear = 5000
    for char in academicYear:
        NumericYear += academicYearDict[char]
    return NumericYear

def semesterToNumber(semester: str) -> int:
    # input: א
    # output: 1
    semesterToNumberDict={"א": 1, "ב": 2, "ק": 3 , "ש": 4}
    return semesterToNumberDict[semester]

def get_course_id(courseObj: CourseData) -> str:
    academicYear=academicYearToNumber(courseObj.academicYear)
    semesterNumber=semesterToNumber(courseObj.semester)
    courseIdentifierAndGroup=courseObj.courseIdentifierAndGroup
    courseIdentifier=courseIdentifierAndGroup.split("-")[1]
    group=courseIdentifierAndGroup.split("-")[2]
    courseID=f"{academicYear}-{semesterNumber}-{courseIdentifier}"
    return courseID , group

# Database schema:
# Database: HIT_Statistics_Database
# Collection: courses
# Document structure:
# {
#   "_id": ObjectId(f"{academicYear}-{semesterNumber}-{courseIdentifier}"),
#   "course_id": "string",
#   "academicYear": "string",
#   "semester": "string",
#   "name": "string",
#   "lecturers": {"01": "string", "02": "string", ...} | None,
#   "finalGradeDistributionAll": list,
#   "finalGradeDistributionGroup": {"01": list, "02": list, ...},
#   "assignments": {
#       "assignment_0": {
#          "name": "string",
#         "instances": {
#             "instance_0": {
#                 "instanceDescription": "string",
#                 "gradeDistributionAll": list,
#                 "gradeDistributionGroup": {"01": list, "02": list, ...}
#             },
#             ...
#         }
#     },
#    ...
# }
# Collection: logs
# Document structure:
# {
#   "_id": ObjectId(),
#   "timestamp": datetime,
#   "numberOfCourses": int,
# }





@app.post("/update-database")
def update_database(request: updateDatabaseRequest):
    coursesData = request.coursesData
    coursesCount=len(coursesData)
    for courseKey in coursesData:
        courseObj=CourseData(**coursesData[courseKey])
        courseID , group = get_course_id(courseObj)
        courseDocument={
            "_id": courseID,
            "course_id": courseID.split("-")[2],
            "academicYear": courseObj.academicYear,
            "semester": courseObj.semester,
            "name": courseObj.name,
            f"lecturers.{group}": courseObj.lecturer,
            "finalGradeDistributionAll": courseObj.finalGradeDistributionAll,
            f"finalGradeDistributionGroup.{group}": courseObj.finalGradeDistributionGroup
        }
        for assignmentKey in courseObj.assignments:
            baseAssignmentPath=f"assignments.{assignmentKey}"
            assignmentObj=AssignmentData(**courseObj.assignments[assignmentKey])
            courseDocument[f"{baseAssignmentPath}.name"] = assignmentObj.name

            for instanceKey in assignmentObj.instances:
                baseInstancePath=f"{baseAssignmentPath}.instances.{instanceKey}"
                instanceObj=InstanceData(**assignmentObj.instances[instanceKey])
                courseDocument[f"{baseInstancePath}.instanceDescription"] = instanceObj.instanceDescription
                courseDocument[f"{baseInstancePath}.gradeDistributionAll"] = instanceObj.gradeDistributionAll
                courseDocument[f"{baseInstancePath}.gradeDistributionGroup.{group}"] = instanceObj.gradeDistributionGroup
        # Upsert the document into MongoDB
        client.HIT_Statistics_Database.courses.update_one(
            {"_id": courseID},
            {"$set": courseDocument},
            upsert=True
        )

    # Log the update
    logEntry = {
        "timestamp": request.logEntry.get("timestamp"),
        "numberOfCourses": coursesCount,
    }
    client.HIT_Statistics_Database.logs.insert_one(logEntry)
    return {"message": f"Successfully updated database with {coursesCount} courses."}


@app.get("/get-courses")
def get_courses_as_metadata():
    coursesCursor = client.HIT_Statistics_Database.courses.find({}, {"_id": 1, "course_id": 1, "academicYear": 1, "semester": 1, "name": 1})
    coursesList = list(coursesCursor)
    for course in coursesList:
        course["_id"] = str(course["_id"])
    return {"courses": coursesList}

@app.get ("/get-course/{course_id}")
def get_course_history_by_id(course_id: str):
    #find all courses with course_id
    coursesCursor = client.HIT_Statistics_Database.courses.find({"course_id": course_id})
    coursesList = list(coursesCursor)
    for course in coursesList:
        course["_id"] = str(course["_id"])
    return {"courses": coursesList}

@app.get ("/get-course/{course_id}/{academic_year}/{semester}")
def get_course_history_by_id_and_year_and_semester(course_id: str, academic_year: str, semester: str):
    courseID=f"{academicYearToNumber(academic_year)}-{semesterToNumber(semester)}-{course_id}"
    course = client.HIT_Statistics_Database.courses.find_one({"_id": courseID})
    if course:
        course["_id"] = str(course["_id"])
        return {"course": course}
    else:
        return {"message": "Course not found."}

