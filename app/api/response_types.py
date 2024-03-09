from typing import Literal, TypedDict

from app.system.smind.vec import ResultChunk


SourceResponse = TypedDict('SourceResponse', {
    "source": str,
})
SourceListResponse = TypedDict('SourceListResponse', {
    "sources": list[str],
})
VersionResponse = TypedDict('VersionResponse', {
    "app_name": str,
    "app_commit": str,
    "python": str,
})
AddEmbed = TypedDict('AddEmbed', {
    "snippets": int,
    "failed": int,
})
QueryEmbed = TypedDict('QueryEmbed', {
    "hits": list[ResultChunk],
    "status": Literal["ok", "error"],
})
