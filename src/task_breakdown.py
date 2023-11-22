# base python things
import os
from dotenv import load_dotenv

# external deps
import llama_index
from llama_index import StorageContext, load_index_from_storage
from llama_index.prompts import PromptTemplate

# internal modules
from src.model_context import get_watsonx_context

# internal tools
from tools.ols_logger import OLSLogger

load_dotenv()

DEFAULT_MODEL = os.getenv("TASK_BREAKDOWN_MODEL", "ibm/granite-13b-chat-v1")


class TaskBreakdown:
    def __init__(self):
        self.logger = OLSLogger("task_breakdown").logger

    def breakdown_tasks(self, conversation, query, **kwargs):
        if "model" in kwargs:
            model = kwargs["model"]
        else:
            model = DEFAULT_MODEL

        if "verbose" in kwargs:
            if kwargs["verbose"] == "True" or kwargs["verbose"] == "true":
                verbose = True
            else:
                verbose = False
        else:
            verbose = False

        # make llama index show the prompting
        if verbose == True:
            llama_index.set_global_handler("simple")

        settings_string = f"conversation: {conversation}, query: {query},model: {model}, verbose: {verbose}"
        self.logger.info(conversation + " call settings: " + settings_string)

        summary_task_breakdown_template_str = """
The following documentation contains a task list. Your job is to extract the list of tasks. If the user-supplied query seems unrelated to the list of tasks, please reply that you do not know what to do with the query and the summary documentation. Use only the supplied content and extract the task list.

Summary document:
{context_str}

User query:
{query_str}

What are the tasks?
"""
        summary_task_breakdown_template = PromptTemplate(
            summary_task_breakdown_template_str
        )

        self.logger.info(conversation + " Getting sevice context")
        self.logger.info(conversation + " using model: " + model)
        service_context = get_watsonx_context(model=model)

        storage_context = StorageContext.from_defaults(persist_dir="vector-db")
        self.logger.info(conversation + " Setting up index")
        index = load_index_from_storage(
            storage_context=storage_context,
            index_id="summary",
            service_context=service_context,
        )

        self.logger.info(conversation + " Setting up query engine")
        query_engine = index.as_query_engine(
            text_qa_template=summary_task_breakdown_template,
            verbose=verbose,
            streaming=False,
            similarity_top_k=1,
        )

        self.logger.info(conversation + " Submitting task breakdown query")
        task_breakdown_response = query_engine.query(query)

        referenced_documents = ""
        for source_node in task_breakdown_response.source_nodes:
            # print(source_node.node.metadata['file_name'])
            referenced_documents += source_node.node.metadata["file_name"] + "\n"

        for line in str(task_breakdown_response).splitlines():
            self.logger.info(conversation + " Task breakdown response: " + line)
        for line in referenced_documents.splitlines():
            self.logger.info(conversation + " Referenced documents: " + line)

        return str(task_breakdown_response).splitlines(), referenced_documents


if __name__ == "__main__":
    """to execute, from the repo root, use python -m modules.task_breakdown.py"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Search the RAG and find a summary document with tasks"
    )
    parser.add_argument(
        "-c",
        "--conversation-id",
        default="1234",
        type=str,
        help="A short identifier for the conversation",
    )
    parser.add_argument(
        "-q",
        "--query",
        default="What is the weather like today?",
        type=str,
        help="The user query to use",
    )
    parser.add_argument(
        "-m", "--model", default=DEFAULT_MODEL, type=str, help="The model to use"
    )
    parser.add_argument(
        "-v",
        "--verbose",
        default=False,
        help="Set Verbose status of langchains [True/False]",
    )

    args = parser.parse_args()

    task_breakdown = TaskBreakdown()
    task_breakdown.breakdown_tasks(
        args.conversation_id, args.query, model=args.model, verbose=args.verbose
    )
