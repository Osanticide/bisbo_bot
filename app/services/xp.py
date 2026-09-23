class XPService:
    """Regras de concessão de XP de perfil."""

    MESSAGES_PER_REWARD = 5
    XP_PER_REWARD = 10

    def __init__(self, profile_repository):
        self.profiles = profile_repository

    async def process_message(self, user_id: int) -> dict:
        return await self.profiles.register_valid_message(user_id)
