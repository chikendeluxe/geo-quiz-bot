"""
Logique d'une session de quiz.
Les joueurs tapent leur réponse dans le chat.
Le drapeau s'affiche en vrai image (flagcdn.com).
"""

import asyncio
import unicodedata
import discord
from questions import generate_questions
from map_generator import generate_country_map

QUESTION_TIMEOUT   = 10   # secondes par question
INTER_QUESTION_GAP = 3    # secondes entre deux questions


def _normalize(text: str) -> str:
    """Minuscules + suppression des accents pour comparaison flexible."""
    nfkd = unicodedata.normalize("NFKD", text.lower().strip())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _progress_bar(current: int, total: int, width: int = 12) -> str:
    filled = round(width * current / max(total, 1))
    return "█" * filled + "░" * (width - filled)


class QuizSession:
    def __init__(self, channel, bot, question_types, difficulty, num_questions):
        self.channel        = channel
        self.bot            = bot
        self.question_types = question_types
        self.difficulty     = difficulty
        self.num_questions  = num_questions

        self.scores:     dict[int, int] = {}
        self.usernames:  dict[int, str] = {}
        self.questions:  list[dict]     = []
        self.current_idx                = 0
        self.is_active                  = True
        self.task: asyncio.Task | None  = None
        self._stop_event                = asyncio.Event()

    # ── Public ───────────────────────────────────────────────────────────────

    async def start(self):
        self.questions = generate_questions(
            self.question_types, self.difficulty, self.num_questions
        )
        try:
            for i, question in enumerate(self.questions):
                if not self.is_active:
                    break
                self.current_idx = i
                await self._ask_question(i, question)
                if self.is_active:
                    await asyncio.sleep(INTER_QUESTION_GAP)

            if self.is_active:
                await self._show_final_scores()
        except asyncio.CancelledError:
            pass
        finally:
            self.is_active = False

    def stop(self):
        self.is_active = False
        self._stop_event.set()
        if self.task:
            self.task.cancel()

    def get_scores_embed(self) -> discord.Embed:
        embed = discord.Embed(title="🏆 Scores en cours", color=0xF1C40F)
        if not self.scores:
            embed.description = "Aucun point pour l'instant."
        else:
            lines = [
                f"**{self.usernames.get(uid, '?')}** : {pts} pt{'s' if pts != 1 else ''}"
                for uid, pts in sorted(self.scores.items(), key=lambda x: -x[1])
            ]
            embed.description = "\n".join(lines)
        embed.set_footer(
            text=f"Question {self.current_idx + 1} / {self.num_questions}  "
                 f"[{_progress_bar(self.current_idx + 1, self.num_questions)}]"
        )
        return embed

    # ── Privé ────────────────────────────────────────────────────────────────

    async def _ask_question(self, idx: int, question: dict):
        embed = self._build_question_embed(idx, question)
        file: discord.File | None = None

        # Image du drapeau via flagcdn.com
        if question["type"] == "flag":
            embed.set_image(
                url=f"https://flagcdn.com/w640/{question['iso2'].lower()}.png"
            )

        # Carte générée dynamiquement
        elif question["type"] == "map":
            try:
                map_io = await generate_country_map(question["country_en"])
                file   = discord.File(map_io, filename="carte.png")
                embed.set_image(url="attachment://carte.png")
            except Exception as exc:
                print(f"[map_generator] Erreur : {exc}")

        if file:
            await self.channel.send(embed=embed, file=file)
        else:
            await self.channel.send(embed=embed)

        # ── Collecte des réponses texte ───────────────────────────────────
        correct_ids:   set[int]           = set()
        correct_users: list[discord.User] = []

        def check(m: discord.Message) -> bool:
            return (
                m.channel.id == self.channel.id
                and not m.author.bot
                and m.author.id not in correct_ids  # peut retenter tant qu'on n'a pas trouvé
            )

        end_time = asyncio.get_event_loop().time() + QUESTION_TIMEOUT

        while self.is_active:
            remaining = end_time - asyncio.get_event_loop().time()
            if remaining <= 0:
                break
            try:
                reply = await asyncio.wait_for(
                    self.bot.wait_for("message", check=check),
                    timeout=min(remaining, 1.0),
                )
                is_correct = _normalize(reply.content) == _normalize(question["answer"])

                if is_correct:
                    correct_ids.add(reply.author.id)
                    correct_users.append(reply.author)
                    asyncio.create_task(reply.add_reaction("✅"))
                    break  # bonne réponse → question suivante immédiatement

            except asyncio.TimeoutError:
                if asyncio.get_event_loop().time() >= end_time:
                    break

        if not self.is_active:
            return

        # ── Mise à jour des scores ────────────────────────────────────────
        for user in correct_users:
            uid = user.id
            if uid not in self.scores:
                self.scores[uid]    = 0
                self.usernames[uid] = user.display_name
            self.scores[uid] += 1

        await self.channel.send(embed=self._build_result_embed(idx, question, correct_users))

    # ── Builders d'embeds ────────────────────────────────────────────────────

    def _build_question_embed(self, idx: int, question: dict) -> discord.Embed:
        total = self.num_questions
        bar   = _progress_bar(idx + 1, total)

        type_to_color = {"flag": 0x3498DB, "capital": 0x9B59B6, "map": 0xE67E22}
        color = type_to_color.get(question["type"], 0x3498DB)

        if question["type"] == "flag":
            desc = "🚩 **De quel pays est ce drapeau ?**"
        elif question["type"] == "capital":
            desc = question["text"]
        else:
            desc = question["text"]

        desc += "\n\n*✏️ Écrivez votre réponse dans le chat !*"

        embed = discord.Embed(
            title=f"Question {idx + 1} / {total}  [{bar}]",
            description=desc,
            color=color,
        )
        embed.set_footer(text=f"⏱️  {QUESTION_TIMEOUT} secondes pour répondre !")
        return embed

    def _build_result_embed(
        self, idx: int, question: dict, correct_users: list
    ) -> discord.Embed:
        embed = discord.Embed(
            title=f"📊 Résultat – Question {idx + 1}",
            color=0x2ECC71 if correct_users else 0xE74C3C,
        )
        embed.add_field(
            name="✅ Bonne réponse",
            value=f"**{question['answer']}**",
            inline=False,
        )

        if correct_users:
            names = ", ".join(f"**{u.display_name}**" for u in correct_users)
            embed.add_field(name="🎉 Bravo !", value=names, inline=False)
        else:
            embed.add_field(
                name="😅 Personne n'a trouvé !",
                value="Mieux vaut la prochaine fois…",
                inline=False,
            )

        if len(self.scores) > 1:
            lines = [
                f"**{self.usernames.get(uid, '?')}** : {pts} pt{'s' if pts != 1 else ''}"
                for uid, pts in sorted(self.scores.items(), key=lambda x: -x[1])
            ]
            embed.add_field(name="🏆 Scores", value="\n".join(lines), inline=False)

        return embed

    async def _show_final_scores(self):
        if not self.scores:
            await self.channel.send(
                embed=discord.Embed(
                    title="🏁 Quiz Terminé !",
                    description="Aucun joueur n'a participé… Quiz désert 🌵",
                    color=0xE74C3C,
                )
            )
            return

        sorted_scores = sorted(self.scores.items(), key=lambda x: -x[1])
        medals = ["🥇", "🥈", "🥉"]
        lines  = [
            f"{medals[i] if i < 3 else f'#{i+1}'} **{self.usernames.get(uid, 'Inconnu')}** : "
            f"{pts} / {self.num_questions} pt{'s' if pts != 1 else ''}"
            for i, (uid, pts) in enumerate(sorted_scores)
        ]

        embed = discord.Embed(
            title="🏁 Quiz Terminé ! Résultats finaux",
            description="\n".join(lines),
            color=0xF1C40F,
        )
        embed.set_footer(text="Merci d'avoir joué ! · /quiz pour rejouer")
        await self.channel.send(embed=embed)
