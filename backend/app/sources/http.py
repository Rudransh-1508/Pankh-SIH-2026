from collections.abc import AsyncIterator
from typing import Annotated

import httpx
from fastapi import Depends


class SourceUnavailable(Exception):
    """A Source System or Data Source could not be reached or answered with an error."""


async def get_source_http() -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(timeout=httpx.Timeout(15, connect=5)) as client:
        yield client


SourceHttp = Annotated[httpx.AsyncClient, Depends(get_source_http)]


def raise_for_source(response: httpx.Response, source: str) -> None:
    if response.status_code >= 500:
        raise SourceUnavailable(f"{source} answered {response.status_code}")
