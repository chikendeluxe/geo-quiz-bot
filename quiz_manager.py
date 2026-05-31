"""
QuizManager – gère les sessions actives (une par salon).
"""

import asyncio
import discord
from quiz_session import QuizSession


class QuizManager:
    def __init__(self, bot: discord.Client):
        self.bot      = bot
        self._sessions: dict[int, QuizSession] = {}   # channel_id → session

    # ── Accesseurs ────────────────────────────────────────────────────────────

    def is_active(self, channel_id: int) -> bool:
        return channel_id in self._sessions

    def get_session(self, channel_id: int) -> QuizSession | None:
        return self._sessions.get(channel_id)

    # ── Actions ───────────────────────────────────────────────────────────────

    async def start_quiz(
        self,
        channel: discord.TextChannel,
        question_types: list[str],
        difficulty: str,
        num_questions: int,
    ) -> None:
        """Crée et démarre une nouvelle session dans le salon."""
        session = QuizSession(channel, question_types, difficulty, num_questions)
        self._sessions[channel.id] = session

        task = asyncio.create_task(session.start())
        session.task = task

        # Nettoyage automatique à la fin
        def _cleanup(t: asyncio.Task):
            self._sessions.pop(channel.id, None)

        task.add_done_callback(_cleanup)

    async def stop_quiz(self, channel_id: int) -> None:
        """Arrête la session en cours dans le salon."""
        session = self._sessions.pop(channel_id, None)
        if session:
            session.stop()
            if session.task:
                try:
                    await asyncio.wait_for(
                        asyncio.shield(session.task), timeout=2.0
                    )
                except (asyncio.TimeoutError, asyncio.CancelledError):
                    pass

    def get_scores_embed(self, channel_id: int) -> discord.Embed | None:
        session = self._sessions.get(channel_id)
        return session.get_scores_embed() if session else None
