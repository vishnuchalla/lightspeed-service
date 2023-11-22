import os
import uuid
from dotenv import load_dotenv
from fastapi import APIRouter
from src.model_context import get_watsonx_predictor
from tools.ols_logger import OLSLogger
from app.models.models import LLMRequest

load_dotenv()

router = APIRouter(prefix="/base_llm_completion", tags=["base_llm_completion"])


def get_suid():
    return str(uuid.uuid4().hex)


@router.post("")
def base_llm_completion(llm_request: LLMRequest):
    base_completion_model = os.getenv(
        "BASE_COMPLETION_MODEL", "ibm/granite-20b-instruct-v1"
    )
    logger = OLSLogger("base_llm_completion_endpoint").logger
    conversation = get_suid()

    llm_response = LLMRequest(query=llm_request.query)
    llm_response.conversation_id = conversation

    logger.info(conversation + " New conversation")

    logger.info(conversation + " Incoming request: " + llm_request.query)
    bare_llm = get_watsonx_predictor(model=base_completion_model)

    response = bare_llm(llm_request.query)

    # TODO: make the removal of endoftext some kind of function
    clean_response = response.split("<|endoftext|>")[0]
    llm_response.response = clean_response

    logger.info(conversation + " Model returned: " + llm_response.response)

    return llm_response
