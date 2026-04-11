from datetime import datetime, timedelta, timezone
from fastapi import FastAPI
import os
from fastapi import FastAPI
from typing import Optional
from pydantic import BaseModel
from dotenv import load_dotenv
from pymongo import MongoClient
from fastapi.middleware.cors import CORSMiddleware
import numpy as np


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
    coursesCursor = client.HIT_Statistics_Database.courses.find({}, {"_id": 1, "course_id": 1, "name": 1})
    coursesList = list(coursesCursor)
    for course in coursesList:
        course["_id"] = str(course["_id"])
    #collapse all courses with the same course_id into one course
    collapsedCourses = {}
    for course in coursesList:
        course_id = course["course_id"]
        if course_id not in collapsedCourses:
            collapsedCourses[course_id] = course
    return {"courses": list(collapsedCourses.values())}


# Course History Structure:
# {
#   "course_id": "string",
#   "name": "string",  (will be determined by the last time the course was held with a name in hebrew)
#   "all_time_stats": {
#       "all_time_average": float, (the average of the final grade distribution of all the times the course was held)
#       "all_time_count": int (the number of students overall)
#       "all_time_median": float (the median of the final grade distribution of all the times the course was held)
#       "all_time_25_percentile": float (the 25th percentile of the final grade distribution of all the times the course was held)
#       "all_time_75_percentile": float (the 75th percentile of the final grade distribution of all the times the course was held)
#       "all_time_bell_curve_diagram": list (list of 20 ints - list[i] represents the number of students that got a final grade in the range (i*5, (i+1)*5] with the exception of list[0] which represents the number of students that got a final grade in the range [0, 5])
#       "all_time_fail_rate": float (the percentage of students that got a final grade in the range [0, 59])
#       "all_time_90_plus_rate": float (the percentage of students that got a final grade in the range [90, 100])
#   },
#   "history":{
#       "academicYear-semester": {
#           "assignments": list
#           "average": float (the average of the final grade distribution of this time the course was held),
#           "count": int (the number of students this time the course was held),
#           "median": float (the median of the final grade distribution of this time the course was held),
#           "25_percentile": float (the 25th percentile of the final grade distribution of this time the course was held),
#           "75_percentile": float (the 75th percentile of the final grade distribution of this time the course was held),
#           "bell_curve_diagram": list (list of 20 ints - list[i] represents the number of students that got a final grade in the range (i*5, (i+1)*5] with the exception of list[0] which represents the number of students that got a final grade in the range [0, 5])
#           "groups_averages": dict (a dictionary where the keys are the groups and the values are the average of the final grade distribution of this time the course was held for each group) 
#           "groups_counts": dict (a dictionary where the keys are the groups and the values are the count of the final grade distribution of this time the course was held for each group)
#           "groups_lecturers": dict (a dictionary where the keys are the groups and the values are the lecturers of this time the course was held for each group)
#           "fail_rate": float (the percentage of students that got a final grade in the range [0, 59] this time the course was held)
#           "90_plus_rate": float (the percentage of students that got a final grade in the range [90, 100] this time the course was held)
#        },
#       ...
#  }


def calculate_bell_curve_diagram(gradeDistribution):
    bell_curve_diagram = [0] * 20
    for grade in gradeDistribution:
        if grade == 0:
            bell_curve_diagram[0] += 1
        else:
            index = min(int((grade-1) // 5), 19)
            bell_curve_diagram[index] += 1
    return bell_curve_diagram

@app.get ("/get-course/{course_id}")
def get_course_history_by_id(course_id: str):
    #find all courses with course_id
    coursesCursor = client.HIT_Statistics_Database.courses.find({"course_id": course_id})
    coursesList = list(coursesCursor)
    if len (coursesList) == 0:
        return {"message": "Error: Course not found."}
    for course in coursesList:
        course["_id"] = str(course["_id"])
    
    engChars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

    courseHistorySummary={}
    courseHistorySummary["course_id"]=course_id
    courseHistorySummary["name"]=""
    for course in coursesList:
        if course["name"][0] in engChars:
            continue
        courseHistorySummary["name"]=course["name"]
        break
    if courseHistorySummary["name"]=="":
        courseHistorySummary["name"]=coursesList[0]["name"]

    all_time_final_grade_distributions = []
    courseHistorySummary["history"]={}
    courseHistorySummary["all_time_stats"]={
        "all_time_average": None,
        "all_time_count": 0,
        "all_time_median": None,
        "all_time_25_percentile": None,
        "all_time_75_percentile": None,
        "all_time_bell_curve_diagram": [0] * 20
    }
    for course in coursesList:
        if "finalGradeDistributionAll" in course and course["finalGradeDistributionAll"] is not None:
            all_time_final_grade_distributions+=course["finalGradeDistributionAll"]
            courseHistorySummary["all_time_stats"]["all_time_count"] += len(course["finalGradeDistributionAll"])

        currentGradeDistribution = course.get("finalGradeDistributionAll")
        courseHistorySummary["history"][f"{course['academicYear']}-{course['semester']}"]={
            "assignments": [assignment["name"] for key, assignment in course.get("assignments", {}).items()],
            "average": np.mean(currentGradeDistribution) if currentGradeDistribution else None,
            "count": len(currentGradeDistribution) if currentGradeDistribution else 0,
            "median": np.median(currentGradeDistribution) if currentGradeDistribution else None,
            "25_percentile": np.percentile(currentGradeDistribution, 25) if currentGradeDistribution else None,
            "75_percentile": np.percentile(currentGradeDistribution, 75) if currentGradeDistribution else None,
            "bell_curve_diagram": calculate_bell_curve_diagram(currentGradeDistribution) if currentGradeDistribution else [0] * 20,
            "groups_averages": {
                group: np.mean(distribution) if distribution else None 
                for group, distribution in course.get("finalGradeDistributionGroup", {}).items()
            } if course.get("finalGradeDistributionGroup") else {},
            
            "groups_counts": {
                group: len(distribution) if distribution else 0 
                for group, distribution in course.get("finalGradeDistributionGroup", {}).items()
            } if course.get("finalGradeDistributionGroup") else {},
            
            "groups_lecturers": {group: lecturer for group, lecturer in course.get("lecturers", {}).items()} if course.get("lecturers") else {},
            "fail_rate": round(len([grade for grade in currentGradeDistribution if grade < 60]) / len(currentGradeDistribution), 2) if currentGradeDistribution else None,
            "90_plus_rate": round(len([grade for grade in currentGradeDistribution if grade >= 90]) / len(currentGradeDistribution), 2) if currentGradeDistribution else None
        }
    # Calculate all time stats
    if len(all_time_final_grade_distributions) > 0:
        courseHistorySummary["all_time_stats"]["all_time_average"] = np.mean(all_time_final_grade_distributions)
        courseHistorySummary["all_time_stats"]["all_time_median"] = np.median(all_time_final_grade_distributions)
        courseHistorySummary["all_time_stats"]["all_time_25_percentile"] = np.percentile(all_time_final_grade_distributions, 25)
        courseHistorySummary["all_time_stats"]["all_time_75_percentile"] = np.percentile(all_time_final_grade_distributions, 75)
        courseHistorySummary["all_time_stats"]["all_time_bell_curve_diagram"] = calculate_bell_curve_diagram(all_time_final_grade_distributions)
        courseHistorySummary["all_time_stats"]["all_time_fail_rate"] = round(len([grade for grade in all_time_final_grade_distributions if grade < 60]) / len(all_time_final_grade_distributions), 4)
        courseHistorySummary["all_time_stats"]["all_time_90_plus_rate"] = round(len([grade for grade in all_time_final_grade_distributions if grade >= 90]) / len(all_time_final_grade_distributions), 4)
    return {"course_history_summary": courseHistorySummary}
    

@app.get ("/get-course/{course_id}/{academic_year}/{semester}")
def get_course_history_by_id_and_year_and_semester(course_id: str, academic_year: str, semester: str):
    courseID=f"{academicYearToNumber(academic_year)}-{semesterToNumber(semester)}-{course_id}"
    course = client.HIT_Statistics_Database.courses.find_one({"_id": courseID})
    if course:
        course["_id"] = str(course["_id"])
        return {"course": course}
    else:
        return {"message": "Course not found."}
    


