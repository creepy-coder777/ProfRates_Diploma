from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Answer(BaseModel):
    model_config = ConfigDict(extra='forbid')
    QuestionID: int = Field(gt=0, strict=True)
    Score: int = Field(ge=1, le=5, strict=True)


class RatingInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    LecturerID: int = Field(gt=0, strict=True)
    CourseID: int = Field(gt=0, strict=True)
    TermID: int = Field(gt=0, strict=True)
    Comment: str | None = Field(default=None, max_length=350)
    answers: list[Answer] = Field(min_length=1)

    @model_validator(mode='after')
    def unique_questions(self):
        if len({a.QuestionID for a in self.answers}) != len(self.answers):
            raise ValueError('QuestionID values must be unique')
        self.Comment = self.Comment.strip() or None if self.Comment else None
        return self


class RatingEdit(RatingInput):
    expected_updated_at: datetime


class PrivateRating(BaseModel):
    RatingID: int
    LecturerID: int
    CourseID: int | None
    TermID: int | None
    Comment: str | None
    Status: str
    CreatedAt: datetime
    UpdatedAt: datetime
    EditExpiry: datetime | None
    answers: list[Answer]


class PublicRating(BaseModel):
    Likes: int
    Dislikes: int
    RatingID: int
    LecturerID: int
    OverallScore: float | None
    Comment: str | None
    CreatedAt: datetime
