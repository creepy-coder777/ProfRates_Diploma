from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Short = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]
ID = Annotated[int, Field(gt=0)]

class Input(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)

class LecturerInput(Input):
    FirstName: Annotated[str, Field(min_length=1,max_length=150)]
    MiddleName: Annotated[str | None, Field(max_length=150)] = None
    LastName: Annotated[str | None, Field(max_length=150)] = None
    Title: Annotated[str | None, Field(max_length=100)] = None
    PhotoUrl: Annotated[str | None, Field(max_length=500)] = None
    Description: Annotated[str | None, Field(max_length=10000)] = None
    IsActive: bool = True
    @model_validator(mode='after')
    def photo(self):
        if self.PhotoUrl and (not self.PhotoUrl.startswith(('https://','/frontend/')) or self.PhotoUrl.startswith('//')):
            raise ValueError('Նկարի հասցեն պետք է լինի https:// կամ /frontend/ հասցե։')
        return self

class UnitInput(Input):
    Name: Name
    ShortName: Short
    IsActive: bool = True

class ChairInput(UnitInput):
    InstituteID: ID | None = None
    FacultyID: ID | None = None
    @model_validator(mode='after')
    def parent(self):
        if (self.InstituteID is None) == (self.FacultyID is None):
            raise ValueError('Ընտրեք միայն մեկ ինստիտուտ կամ ֆակուլտետ։')
        return self

class SpecializationInput(Input):
    ChairID: ID
    Name: Name
    Code: Annotated[str, StringConstraints(strip_whitespace=True,min_length=1,max_length=20)]
    IsActive: bool = True

class GroupInput(Input):
    GroupCode: Annotated[str, Field(min_length=1,max_length=20)]
    SpecializationID: ID
    EnrollmentYear: Annotated[int, Field(ge=2000,le=2100)]
    IsActive: bool = True

class CourseInput(Input):
    SpecializationID: ID
    LecturerID: ID
    Name: Name
    CurriculumSemesterNumber: Annotated[int, Field(ge=1,le=20)]
    IsActive: bool = True

class StudentCourseInput(Input):
    UserID: ID
    CourseID: ID

class Assignment(Input):
    LecturerID: ID

class QuestionInput(Input):
    Text: Annotated[str, Field(min_length=1,max_length=500)]
    Category: Annotated[str, Field(min_length=1,max_length=100)]
    SortOrder: Annotated[int, Field(ge=0,le=1000000)]
    IsActive: bool = True

class Reorder(Input):
    question_ids: Annotated[list[ID], Field(min_length=1,max_length=1000)]
    @model_validator(mode='after')
    def unique(self):
        if len(self.question_ids) != len(set(self.question_ids)):
            raise ValueError('Հարցերը կրկնվում են։')
        return self

class Moderation(Input):
    status: Literal['Approved','Rejected']
    expected_status: Literal['Pending','Approved','Rejected']
