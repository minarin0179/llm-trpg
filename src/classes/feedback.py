from pydantic import BaseModel
from datetime import datetime


class Feedback(BaseModel):
    comment: str
    result: bool

    def to_dict(self):
        return {
            "comment": self.comment,
            "result": self.result
        }


class FeedbackWithLog(Feedback):
    created: str
    usage: dict

    def to_dict(self):
        return {
            "comment": self.comment,
            "result": self.result,
            "created": self.created,
            "usage": self.usage
        }


def feedback_to_dict(obj):
    if isinstance(obj, FeedbackWithLog):
        return obj.to_dict()
    raise TypeError(f"Object of type '{
                    obj.__class__.__name__}' is not JSON serializable")
