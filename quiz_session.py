"""
Logique d'une session de quiz :
  • QuizSession   – gère le déroulement complet (questions, scores, arrêt)
  • QuizAnswerView / AnswerButton – UI Discord (boutons A/B/C/D)
"""

import asyncio
import discord
from questions import generate_questions
from map_generator import generate_country_map

QUESTION_TIMEOUT   = 15   # secondes par question
INTER_QUESTION_GAP = 3    # secondes entre deux questions

# Palette de couleurs des boutons (cyclée sur les 4 choix)
_BTN_STYLES = [
    discord.ButtonStyle.primary,
    discord.ButtonStyle.success,
    discord.ButtonStyle.danger,
    discord.ButtonStyle.secondary,
]

# ── UI ────────────────────────────────────────────────────────────────────────

class AnswerButton(discord.ui.Button):
    def __init__(self, label: str, choice: str, index: int):
        super().__init__(label=label[:80], style=_BTN_STYLES[index % 4])
        self.choice = choice

    async def callback(self, interaction: discord.Interaction):
        view: QuizAnswerView = self.view  # type: ignore

        if view.is_ended:
            await interaction.response.send_message("⏰ Temps écoulé !", ephemeral=True)
            return

        uid = interaction.user.id
        if uid in view.results:
            await interaction.response.send_message(
                "Tu as déjà répondu à cette question !", ephemeral=True
            )
            return

        is_correct = self.choice == view.correct_answer
        view.results[uid] = (interaction.user, is_correct)

        if is_correct:
            view.correct_users.append(interaction.user)
            await interaction.response.send_message(
                "✅ **Bonne réponse !** +1 point 🎉", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"❌ Mauvaise réponse ! Tu as répondu : **{self.choice}**", ephemeral=True
            )


class QuizAnswerView(discord.ui.View):
    def __init__(self, correct_answer: str, choices: list[str]):
        super().__init__(timeout=float(QUESTION_TIMEOUT))
        self.correct_answer = correct_answer
        self.results:       dict[int, tuple[discord.User, bool]] = {}
        self.correct_users: list[discord.User] = []
        self.is_ended = False

        for i, choice in enumerate(choices):
            self.add_item(AnswerButton(f"{chr(65+i)}. {choice}", choice, i))

    async def on_timeout(self):
        self.is_ended = True
        self.stop()

    def disable_all(self):
        for item in self.children:
            item.disabled = True  # type: ignore


# ── Session ───────────────────────────────────────────────────────────────────

def _progress_bar(current: int, total: int, width: int = 12) -> str:
    filled = round(width * current / max(total, 1))
    return "█" * filled + "░" * (width - filled)


class QuizSession:
    def __init__(
        self,
        channel: discord.TextChannel,
        question_types: list[str],
        difficulty: str,
        num_questions: int,
    ):
        self.channel        = channel
        self.question_types = question_types
        self.difficulty     = difficulty
        self.num_questions  = num_questions

        self.scores:    dict[int, int]  = {}   # uid → points
        self.usernames: dict[int, str]  = {}   # uid → display_name
        self.questions: list[dict]      = []
        self.current_idx                = 0
        self.is_active                  = True
        self.task: asyncio.Task | None  = None
        self._stop_event                = asyncio.Event()

    # ── Public ────────────────────────────────────────────────────────────────

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

    # ── Privé ─────────────────────────────────────────────────────────────────

    async def _ask_question(self, idx: int, question: dict):
        view  = QuizAnswerView(question["answer"], question["choices"])
        embed = self._build_question_embed(idx, question)
        file: discord.File | None = None

        # Génération de la carte pour les questions de type map
        if question["type"] == "map":
            try:
                map_io = await generate_country_map(question["country_en"])
                file   = discord.File(map_io, filename="carte.png")
                embed.set_image(url="attachment://carte.png")
            except Exception as exc:
                print(f"[map_generator] Erreur : {exc}")
                embed.add_field(
                    name="⚠️ Carte indisponible",
                    value="Fichiers cartographiques manquants.",
                    inline=False,
                )

        # Envoi du message
        if file:
            msg = await self.channel.send(embed=embed, file=file, view=view)
        else:
            msg = await self.channel.send(embed=embed, view=view)

        # Attente : fin du timeout OU arrêt du quiz
        wait_view = asyncio.ensure_future(view.wait())
        wait_stop = asyncio.ensure_future(self._stop_event.wait())
        done, pending = await asyncio.wait(
            {wait_view, wait_stop},
            return_when=asyncio.FIRST_COMPLETED,
        )
        for t in pending:
            t.cancel()

        if not self.is_active:
            return

        # Enregistrement des scores
        for uid, (user, correct) in view.results.items():
            if uid not in self.scores:
                self.scores[uid]    = 0
                self.usernames[uid] = user.display_name
            if correct:
                self.scores[uid] += 1

        # Mise à jour du message avec le résultat
        view.disable_all()
        result_embed = self._build_result_embed(idx, question, view)
        try:
            await msg.edit(embed=result_embed, view=view)
        except discord.HTTPException:
            pass

    def _build_question_embed(self, idx: int, question: dict) -> discord.Embed:
        q_type = question["type"]
        total  = self.num_questions
        bar    = _progress_bar(idx + 1, total)

        if q_type == "flag":
            color = 0x3498DB
            desc  = f"# {question['flag_emoji']}\n\nQuel pays est représenté par ce drapeau ?"
        elif q_type == "capital":
            color = 0x9B59B6
            desc  = question["text"]
        else:  # map
            color = 0xE67E22
            desc  = question["text"]

        embed = discord.Embed(
            title=f"Question {idx + 1} / {total}  [{bar}]",
            description=desc,
            color=color,
        )
        embed.set_footer(text=f"⏱️  {QUESTION_TIMEOUT} secondes · Cliquez sur votre réponse !")
        return embed

    def _build_result_embed(
        self, idx: int, question: dict, view: QuizAnswerView
    ) -> discord.Embed:
        embed = discord.Embed(
            title=f"📊 Résultat – Question {idx + 1}",
            color=0x2ECC71 if view.correct_users else 0xE74C3C,
        )
        embed.add_field(
            name="✅ Bonne réponse",
            value=f"**{question['answer']}**",
            inline=False,
        )

        if view.correct_users:
            names = ", ".join(f"**{u.display_name}**" for u in view.correct_users)
            embed.add_field(name="🎉 Bravo !", value=names, inline=False)
        else:
            embed.add_field(
                name="😅 Personne n'a trouvé !",
                value="Mieux vaut la prochaine fois…",
                inline=False,
            )

        # Scores si plusieurs joueurs
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
        lines  = []
        for i, (uid, pts) in enumerate(sorted_scores):
            medal = medals[i] if i < 3 else f"#{i + 1}"
            name  = self.usernames.get(uid, "Inconnu")
            lines.append(
                f"{medal} **{name}** : {pts} / {self.num_questions} pt{'s' if pts != 1 else ''}"
            )

        embed = discord.Embed(
            title="🏁 Quiz Terminé ! Résultats finaux",
            description="\n".join(lines),
            color=0xF1C40F,
        )
        embed.set_footer(text="Merci d'avoir joué ! · /quiz pour rejouer")
        await self.channel.send(embed=embed)
