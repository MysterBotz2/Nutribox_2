from app.repositories.chat_repository import ChatRepository
from app.schemas.chat import ChatConversationResponse, ChatMessageResponse, ChatResponse
from app.services.nutrition_coach_provider import NutritionCoachChatTurn
from app.services.nutrition_coach_service import NutritionCoachService


class ChatConversationNotFoundError(ValueError):
    pass


class ChatService:
    _HISTORY_LIMIT = 12

    def __init__(self, repository: ChatRepository, coach_service: NutritionCoachService) -> None:
        self._repository = repository
        self._coach = coach_service

    async def send(self, user_id: int, timezone_name: str, message: str, conversation_id: int | None) -> ChatResponse:
        conversation = self._repository.create_conversation(user_id) if conversation_id is None else self._repository.get_for_user(conversation_id, user_id)
        if conversation is None:
            raise ChatConversationNotFoundError("Conversation was not found.")
        history = tuple(NutritionCoachChatTurn(role=item.role, content=item.content) for item in conversation.messages[-self._HISTORY_LIMIT:])
        user_message = self._repository.add_message(conversation, "user", message)
        context = self._coach.build_context(user_id, timezone_name, message, history)
        result = await self._coach.generate_chat_reply(context)
        assistant_message = self._repository.add_message(conversation, "assistant", result.message)
        return ChatResponse(conversation_id=conversation.id, user_message=self._message(user_message), assistant_message=self._message(assistant_message))

    def get(self, user_id: int, conversation_id: int) -> ChatConversationResponse:
        conversation = self._repository.get_for_user(conversation_id, user_id)
        if conversation is None:
            raise ChatConversationNotFoundError("Conversation was not found.")
        return self._conversation(conversation)

    def list(self, user_id: int) -> list[ChatConversationResponse]:
        return [self._conversation(item) for item in self._repository.list_for_user(user_id)]

    @staticmethod
    def _message(message) -> ChatMessageResponse:
        return ChatMessageResponse(id=message.id, role=message.role, content=message.content, created_at=message.created_at)

    def _conversation(self, conversation) -> ChatConversationResponse:
        return ChatConversationResponse(id=conversation.id, created_at=conversation.created_at, updated_at=conversation.updated_at, messages=[self._message(message) for message in conversation.messages])
