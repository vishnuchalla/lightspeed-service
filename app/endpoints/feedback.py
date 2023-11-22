from fastapi import APIRouter
from pydantic import BaseModel
from app.models.models import FeedbackRequest
from tools.ols_logger import OLSLogger

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("")
def feedback_request(feedback_request: FeedbackRequest):
    logger = OLSLogger("feedback_endpoint").logger

    conversation = str(feedback_request.conversation_id)
    logger.info(conversation + " New feedback received")
    logger.info(conversation + " Feedback blob: " + feedback_request.feedback_object)

    return {"status": "feedback received"}
