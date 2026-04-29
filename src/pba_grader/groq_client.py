"""Backward-compat shim: ThrottledGroqClient → ThrottledLLMClient.

Module ini di-keep supaya import lama tidak pecah. Kode baru pakai
`pba_grader.llm_client.ThrottledLLMClient` langsung.
"""

from .llm_client import ThrottledLLMClient as ThrottledGroqClient

__all__ = ["ThrottledGroqClient"]
