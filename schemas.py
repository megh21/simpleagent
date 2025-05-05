from pydantic import BaseModel
from typing import List, Optional

class CreateConversationRequest(BaseModel):
    title: str = "New Conversation"

class ConversationMessageRequest(BaseModel):
    query: str
    doc_ids: Optional[List[str]] = None
    include_web_search: bool = False
