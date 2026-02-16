"""
LLM Manager - Enhanced ChatOpenAI with quota management and rate limiting
"""

import time
from typing import Dict, Any, Optional
from collections import defaultdict
from langchain_openai import ChatOpenAI
from openai import RateLimitError
import httpx
import sys
import os

# Add project root to path for imports
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from utils.observability import StructuredLogger, trace_operation

logger = StructuredLogger(__name__)


class LLMQuotaManager:
    """Manages OpenAI API quota, rate limiting, and model fallback"""

    # Model fallback hierarchy (from most capable to least expensive)
    MODEL_FALLBACK_CHAIN = [
        # "gpt-5-mini",       # Primary - GPT-5 mini for orchestrator
        "gpt-4o-mini",  # Fallback 1 - GPT-4o mini
        "gpt-3.5-turbo",  # Fallback 2 - reliable and fast
        "gpt-3.5-turbo-16k",  # Fallback 3 - larger context
    ]

    # Rate limits per model (requests per minute)
    RATE_LIMITS = {
        # "gpt-5-mini": 100,       # Generous rate limit for GPT-5 mini
        # "gpt-5-nano": 200,       # Higher rate limit for GPT-5 nano (agents)
        "gpt-4o-mini": 100,  # Generous rate limit for fallback model
        "gpt-3.5-turbo": 200,  # Higher rate limit for fallback
        "gpt-3.5-turbo-16k": 150,  # Moderate rate limit for final fallback
    }

    def __init__(self):
        self.request_counts = defaultdict(list)  # model -> [timestamps]
        self.quota_exceeded = defaultdict(bool)  # model -> exceeded flag
        self.last_request_time = defaultdict(float)  # model -> timestamp
        self.failed_requests = defaultdict(int)  # model -> fail count
        self.successful_requests = defaultdict(int)  # model -> success count
        logger.info("LLM Quota Manager initialized", models=self.MODEL_FALLBACK_CHAIN)

    def _cleanup_old_requests(self, model: str):
        """Remove request timestamps older than 1 minute"""
        current_time = time.time()
        minute_ago = current_time - 60
        self.request_counts[model] = [
            timestamp
            for timestamp in self.request_counts[model]
            if timestamp > minute_ago
        ]

    def can_make_request(self, model: str) -> bool:
        """Check if we can make a request to the given model"""
        if self.quota_exceeded[model]:
            return False

        self._cleanup_old_requests(model)
        current_requests = len(self.request_counts[model])
        rate_limit = self.RATE_LIMITS.get(model, 50)  # Default conservative limit

        return current_requests < rate_limit

    def record_request(self, model: str, success: bool = True):
        """Record a request attempt"""
        current_time = time.time()
        self.request_counts[model].append(current_time)
        self.last_request_time[model] = current_time

        if success:
            self.successful_requests[model] += 1
            # Reset quota exceeded flag on successful request
            if self.quota_exceeded[model]:
                self.quota_exceeded[model] = False
                logger.info("Quota recovered for model", model=model)
        else:
            self.failed_requests[model] += 1

    def mark_quota_exceeded(self, model: str):
        """Mark a model as having exceeded quota"""
        self.quota_exceeded[model] = True
        logger.warning("Quota exceeded for model", model=model)

    def get_available_model(self) -> Optional[str]:
        """Get the best available model based on rate limits and quotas"""
        for model in self.MODEL_FALLBACK_CHAIN:
            if self.can_make_request(model):
                return model

        logger.error("All models rate limited or quota exceeded")
        return None

    def reset_quotas(self):
        """Reset all quota exceeded flags (for testing or manual recovery)"""
        self.quota_exceeded = defaultdict(bool)
        logger.info("All quota flags reset")

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics for monitoring"""
        stats = {"models": {}, "total_requests": 0, "total_failures": 0}

        for model in self.MODEL_FALLBACK_CHAIN:
            self._cleanup_old_requests(model)
            model_stats = {
                "requests_last_minute": len(self.request_counts[model]),
                "rate_limit": self.RATE_LIMITS.get(model, 50),
                "quota_exceeded": self.quota_exceeded[model],
                "successful_requests": self.successful_requests[model],
                "failed_requests": self.failed_requests[model],
                "can_make_request": self.can_make_request(model),
            }
            stats["models"][model] = model_stats
            stats["total_requests"] += (
                self.successful_requests[model] + self.failed_requests[model]
            )
            stats["total_failures"] += self.failed_requests[model]

        return stats


class EnhancedChatOpenAI(ChatOpenAI):
    """Enhanced ChatOpenAI with intelligent quota management and fallback"""

    def __init__(self, quota_manager: LLMQuotaManager, **kwargs):
        # Initialize with the best available model
        initial_model = (
            quota_manager.get_available_model() or quota_manager.MODEL_FALLBACK_CHAIN[0]
        )
        kwargs["model"] = initial_model
        # Call parent init first
        # Force HTTP/1.1 (disable HTTP/2) via http_client to avoid Cloud Run transport quirks
        try:
            kwargs["http_client"] = httpx.Client(http2=False, timeout=30.0)
        except Exception:
            pass
        super().__init__(**kwargs)
        # Store quota manager as private attribute after calling super().__init__
        self._quota_manager = quota_manager

    def _handle_rate_limit_with_fallback(self, original_error, *args, **kwargs):
        """Handle rate limiting with intelligent model fallback"""
        current_model = self.model_name
        self._quota_manager.mark_quota_exceeded(current_model)

        logger.warning(
            "Rate limit hit, attempting fallback",
            current_model=current_model,
            error=str(original_error),
        )

        # Try each model in the fallback chain
        for fallback_model in self._quota_manager.MODEL_FALLBACK_CHAIN:
            if fallback_model == current_model:
                continue  # Skip the model that just failed

            if self._quota_manager.can_make_request(fallback_model):
                logger.info(
                    "Switching to fallback model",
                    from_model=current_model,
                    to_model=fallback_model,
                )

                # Update model and retry
                old_model = self.model_name
                self.model_name = fallback_model

                try:
                    # Record the attempt
                    self._quota_manager.record_request(fallback_model, success=False)

                    # Retry with new model
                    result = super().invoke(*args, **kwargs)

                    # Success - record it
                    self._quota_manager.record_request(fallback_model, success=True)

                    logger.info(
                        "Fallback successful",
                        fallback_model=fallback_model,
                        original_error=str(original_error),
                    )

                    return result

                except RateLimitError as fallback_error:
                    logger.warning(
                        "Fallback model also rate limited",
                        model=fallback_model,
                        error=str(fallback_error),
                    )
                    self._quota_manager.mark_quota_exceeded(fallback_model)
                    continue  # Try next model

                except Exception as fallback_error:
                    logger.error(
                        "Fallback model failed with different error",
                        model=fallback_model,
                        error=str(fallback_error),
                    )
                    self._quota_manager.record_request(fallback_model, success=False)
                    # Restore original model and continue trying others
                    self.model_name = old_model
                    continue

        # If we get here, all models failed
        logger.error(
            "All fallback models exhausted", original_error=str(original_error)
        )

        # Return a structured error response instead of raising
        return f"Rate limit exceeded on all available models. Original error: {str(original_error)}"

    def invoke(self, *args, **kwargs):
        """Enhanced invoke with quota management"""
        current_model = self.model_name

        with trace_operation("llm.invoke", attributes={"model": current_model}):
            # Check if we can make request
            if not self._quota_manager.can_make_request(current_model):
                logger.warning(
                    "Rate limit check failed, attempting model switch",
                    model=current_model,
                )

                # Try to switch to available model
                available_model = self._quota_manager.get_available_model()
                if available_model and available_model != current_model:
                    logger.info(
                        "Proactively switching models",
                        from_model=current_model,
                        to_model=available_model,
                    )
                    self.model_name = available_model
                    current_model = available_model
                elif not available_model:
                    return (
                        "All models are currently rate limited. Please try again later."
                    )

            try:
                # Record request attempt
                self._quota_manager.record_request(current_model, success=False)

                # Make the actual request
                result = super().invoke(*args, **kwargs)

                # Success - record it
                self._quota_manager.record_request(current_model, success=True)

                return result

            except RateLimitError as e:
                logger.warning(
                    "Rate limit error during request", model=current_model, error=str(e)
                )
                return self._handle_rate_limit_with_fallback(e, *args, **kwargs)

            except Exception as e:
                # Record failure for other errors
                self._quota_manager.record_request(current_model, success=False)
                logger.error("LLM request failed", model=current_model, error=str(e))
                raise
