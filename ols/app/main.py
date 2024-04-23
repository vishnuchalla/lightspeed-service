"""Entry point to FastAPI-based web service."""

import logging
from collections.abc import AsyncGenerator, Awaitable, Callable

from fastapi import FastAPI, Request, Response
from starlette.datastructures import Headers
from starlette.responses import StreamingResponse

from ols import constants
from ols.app import metrics, routers
from ols.src.ui.gradio_ui import GradioUI
from ols.utils import config

app = FastAPI(
    title="Swagger OpenShift LightSpeed Service - OpenAPI",
    description="""OpenShift LightSpeed Service API specification.""",
    license_info={
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    },
)


logger = logging.getLogger(__name__)

if config.dev_config.enable_dev_ui:
    app = GradioUI().mount_ui(app)
else:
    logger.info(
        "Embedded Gradio UI is disabled. To enable set `enable_dev_ui: true` "
        "in the `dev_config` section of the configuration file."
    )


# update provider and model as soon as possible so the metrics will be visible
# even for first scraping
metrics.setup_model_metrics(config.config)


@app.middleware("")
async def rest_api_counter(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Middleware with REST API counter update logic."""
    path = request.url.path

    # measure time to handle duration + update histogram
    with metrics.response_duration_seconds.labels(path).time():
        response = await call_next(request)

    # ignore /metrics endpoint that will be called periodically
    if not path.endswith("/metrics"):
        # just update metrics
        metrics.rest_api_calls_total.labels(path, response.status_code).inc()
    return response


def _log_headers(headers: Headers, to_redact: set[str]) -> str:
    """Serialize headers into a string while redacting sensitive values."""
    pairs = []
    for h, v in headers.items():
        value = "XXXXX" if h.lower() in to_redact else v
        pairs.append(f'"{h}":"{value}"')
    return "Headers({" + ", ".join(pairs) + "})"


@app.middleware("")
async def log_requests_responses(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Middleware for logging of HTTP requests and responses, at debug level."""
    # Bail out early if not logging
    if not logger.isEnabledFor(logging.DEBUG):
        return await call_next(request)

    request_log_message = f"Request from {request.client.host}:{request.client.port} "
    request_log_message += _log_headers(
        request.headers, constants.HTTP_REQUEST_HEADERS_TO_REDACT
    )
    request_log_message += ", Body: "

    request_body = await request.body()
    if request_body:
        request_log_message += f"{request_body.decode('utf-8')}"
    else:
        request_log_message += "None"

    logger.debug(request_log_message)

    response = await call_next(request)

    response_headers_log_message = (
        f"Response to {request.client.host}:{request.client.port} "
    )
    response_headers_log_message += _log_headers(
        response.headers, constants.HTTP_RESPONSE_HEADERS_TO_REDACT
    )
    logger.debug(response_headers_log_message)

    async def stream_response_body(
        response_body: AsyncGenerator[bytes, None]
    ) -> AsyncGenerator[bytes, None]:
        async for chunk in response_body:
            logger.debug(
                f"Response to {request.client.host}:{request.client.port} "
                f"Body chunk: {chunk.decode('utf-8', errors='ignore')}"
            )
            yield chunk

    if isinstance(response, StreamingResponse):
        # The response is already a streaming response
        response.body_iterator = stream_response_body(response.body_iterator)
    else:
        # Convert non-streaming response to a streaming response to log its body
        response_body = response.body
        response = StreamingResponse(stream_response_body(iter([response_body])))

    return response


routers.include_routers(app)
