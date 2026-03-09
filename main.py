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
#   "lastUpdated": datetime,
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



def smart_upsert(collection, filter_query, new_data):
    # 1. We still need to compare the whole doc to see if anything changed
    # Note: Use the 'flatten' function from the previous step if your 
    # new_data is a nested dict.
    
    pipeline = [
        {
            "$set": {
                # The logic remains: if current doc == doc after merging new data
                "last_updated": {
                    "$cond": {
                        "if": { "$eq": ["$$ROOT", { "$mergeObjects": ["$$ROOT", new_data] }] },
                        "then": "$last_updated",
                        "else": datetime.utcnow()
                    }
                }
            }
        }
    ]

    # 2. Instead of **new_data, we manually map each key using $setField
    # This bypasses the "FieldPath names may not contain '.'" error
    for key, value in new_data.items():
        pipeline[0]["$set"][key] = value

    # 3. If the keys HAVE dots (e.g., "a.b.c"), we must use a slightly different 
    # aggregation stage structure or flatten the document.
    
    return collection.update_one(filter_query, pipeline, upsert=True)


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
            "finalGradeDistributionAll": courseObj.finalGradeDistributionAll,
            f"finalGradeDistributionGroup.{group}": courseObj.finalGradeDistributionGroup,
            "lastUpdated": request.logEntry.get("timestamp"),
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
        """client.HIT_Statistics_Database.courses.update_one(
            {"_id": courseID},
            {"$set": courseDocument},
            upsert=True
        )"""
        smart_upsert(client.HIT_Statistics_Database.courses, {"_id": courseID}, courseDocument)

    # Log the update
    logEntry = {
        "timestamp": request.logEntry.get("timestamp"),
        "numberOfCourses": coursesCount,
    }
    client.HIT_Statistics_Database.logs.insert_one(logEntry)
    return {"message": f"Successfully updated database with {coursesCount} courses."}
    


