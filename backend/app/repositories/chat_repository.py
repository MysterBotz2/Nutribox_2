from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.chat import ChatConversation, ChatMessage


class ChatRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_conversation(self, user_id: int) -> ChatConversation:
        conversation = ChatConversation(user_id=user_id)
        self.session.add(conversation)
        self.session.flush()
        return conversation

    def get_for_user(self, conversation_id: int, user_id: int) -> ChatConversation | None:
        return self.session.scalar(select(ChatConversation).options(selectinload(ChatConversation.messages)).where(ChatConversation.id == conversation_id, ChatConversation.user_id == user_id))

    def list_for_user(self, user_id: int) -> list[ChatConversation]:
        return list(self.session.scalars(select(ChatConversation).where(ChatConversation.user_id == user_id).order_by(ChatConversation.updated_at.desc(), ChatConversation.id.desc())))

    def add_message(self, conversation: ChatConversation, role: str, content: str) -> ChatMessage:
        message = ChatMessage(conversation_id=conversation.id, role=role, content=content)
        self.session.add(message)
        self.session.flush()
        return message
