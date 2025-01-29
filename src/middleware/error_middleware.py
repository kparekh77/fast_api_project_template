from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send, ExceptionHandler


class UnhandledExceptionsMiddleware:
    """
    Middleware to catch all unhandled exceptions in the stack with
    an exception handler provider.
    """

    def __init__(
        self,
        app: ASGIApp,
        handler: ExceptionHandler,
    ) -> None:
        self.app: ASGIApp = app
        self._handler = handler

    # See: starlette.middleware.errors.ServerErrorMiddleware
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        response_started = False

        async def _send(message: Message) -> None:
            nonlocal response_started, send
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, receive, _send)
        except Exception as exc:
            if not response_started:
                response = await self._handler(Request(scope), exc)
                await response(scope, receive, send)

            # Continue to raise the exception. This allows the exception to
            # be logged, or optionally allows test clients to raise the error
            # in test cases.
            raise exc from None
