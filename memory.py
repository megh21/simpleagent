from langchain.memory import ConversationBufferMemory
from langchain.schema import SystemMessage, HumanMessage, AIMessage
from typing import List, Dict, Optional, Any
import uuid
from database import add_message, get_conversation_messages
from pydantic import Field

class SQLAlchemyConversationMemory(ConversationBufferMemory):
    """
    A conversation memory that persists messages to SQLAlchemy database.
    """
    
    conversation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    def __init__(self, conversation_id: str = None, return_messages: bool = True, **kwargs):
        super().__init__(return_messages=return_messages, **kwargs)
        if conversation_id:
            self.conversation_id = conversation_id
        self.memory_key = "chat_history"
        self.human_prefix = "Human"
        self.ai_prefix = "AI"
    
    async def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Load the memory variables from the database."""
        if not self.conversation_id:
            return {self.memory_key: []}
        
        db_messages = await get_conversation_messages(self.conversation_id)
        
        # Convert to LangChain message format
        messages = []
        for msg in db_messages:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))
            elif msg["role"] == "system":
                messages.append(SystemMessage(content=msg["content"]))
        
        return {self.memory_key: messages}
    
    async def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, str]) -> None:
        """Save the context of this conversation to the database."""
        if not self.conversation_id:
            return
        
        # Save input (user message)
        if "input" in inputs:
            await add_message(
                conversation_id=self.conversation_id,
                role="user",
                content=inputs["input"]
            )
        
        # Save output (AI message)
        if "output" in outputs:
            metadata = None
            if "sources" in outputs:
                metadata = {"sources": outputs["sources"]}
            if "validation" in outputs:
                if not metadata:
                    metadata = {}
                metadata["validation"] = outputs["validation"]
                
            await add_message(
                conversation_id=self.conversation_id,
                role="assistant",
                content=outputs["output"],
                metadata=metadata
            )
    
    def clear(self) -> None:
        """Clear memory contents."""
        # This method is required but does nothing for database-backed memory
        pass