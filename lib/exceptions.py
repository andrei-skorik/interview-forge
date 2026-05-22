class InterviewForgeError(Exception):
    code: str = "UNKNOWN_ERROR"
    user_message: str = "An unexpected error occurred."

    def __init__(self, detail: str = "") -> None:
        self.detail = detail
        super().__init__(detail or self.user_message)


class ValidationError(InterviewForgeError):
    code = "VALIDATION_ERROR"
    user_message = "Invalid input. Please check your data."


class PromptInjectionError(InterviewForgeError):
    code = "PROMPT_INJECTION_DETECTED"
    user_message = "Your input contains patterns that violate our usage policy. Please rephrase."


class UnauthorizedError(InterviewForgeError):
    code = "UNAUTHORIZED"
    user_message = "You don't have permission to access this resource."


class NotFoundError(InterviewForgeError):
    code = "NOT_FOUND"
    user_message = "Resource not found or you don't have access."


class RateLimitError(InterviewForgeError):
    code = "RATE_LIMIT_EXCEEDED"
    user_message = "Too many requests. Please wait a moment and try again."


class LLMProviderError(InterviewForgeError):
    code = "LLM_PROVIDER_ERROR"
    user_message = "AI service temporarily unavailable. Please try again."


class LLMTimeoutError(InterviewForgeError):
    code = "LLM_TIMEOUT"
    user_message = "The AI provider didn't respond in time. Please try again."
