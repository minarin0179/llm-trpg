from pydantic import BaseModel


class Feedback(BaseModel):
    comment: str
    result: bool

    def to_dict(self):
        return {
            "comment": self.comment,
            "result": self.result
        }


def feedback_to_dict(obj):
    if isinstance(obj, Feedback):
        return obj.to_dict()
    raise
