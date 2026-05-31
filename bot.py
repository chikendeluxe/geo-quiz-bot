"""
Bot Discord – Quiz de Géographie
Commandes disponibles :
  /quiz      – lance un quiz
  /stopquiz  – arrête le quiz en cours
  /scores    – affiche les scores en temps réel
"""

import os
import asyncio
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from quiz_manager import QuizManager

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN", "")

# ── Bot setup ─────────────────────────────────────────────────────────────────

intents = discord.Intents.default()
bot     = commands.Bot(command_prefix="!", intents=intents)
quiz_mgr: QuizManager  # instancié dans on_ready


# ── Labels UI ─────────────────────────────────────────────────────────────────

_TYPE_LABELS = {
    "all":              "🌐 Tous les types",
    "flags":            "🚩 Drapeaux",
    "capitals":         "🏛️ Capitales",
    "maps":             "🗺️ Cartes",
    "flags,capitals":   "🚩🏛️ Drapeaux + Capitales",
    "flags,maps":       "🚩🗺️ Drapeaux + Cartes",
    "capitals,maps":    "🏛️🗺️ Capitales + Cartes",
}

_DIFF_LABELS = {
    "easy":   "🟢 Facile",
    "medium": "🟡 Moyen",
    "hard":   "🔴 Difficile",
    "all":    "🌈 Tous les niveaux",
}

# Type → liste de clés internes
_TYPE_MAP = {
    "all":            ["flag", "capital", "map"],
    "flags":          ["flag"],
    "capitals":       ["capital"],
    "maps":           ["map"],
    "flags,capitals": ["flag", "capital"],
    "flags,maps":     ["flag", "map"],
    "capitals,maps":  ["capital", "map"],
}


# ── Événements ────────────────────────────────────────────────────────────────

@bot.event
async def on_ready():
    global quiz_mgr
    quiz_mgr = QuizManager(bot)

    await bot.tree.sync()
    print(f"✅  Connecté en tant que {bot.user}  (ID : {bot.user.id})")
    print("✅  Commandes slash synchronisées")

    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.playing,
            name="🌍 /quiz pour jouer !",
        )
    )


# ── Commandes ─────────────────────────────────────────────────────────────────

@bot.tree.command(name="quiz", description="🌍 Lance un quiz de géographie !")
@app_commands.describe(
    type="Type de questions à poser",
    difficulty="Niveau de difficulté",
    questions="Nombre de questions (5 à 20)",
)
@app_commands.choices(type=[
    app_commands.Choice(name="🌐 Tous les types",            value="all"),
    app_commands.Choice(name="🚩 Drapeaux seulement",        value="flags"),
    app_commands.Choice(name="🏛️ Capitales seulement",      value="capitals"),
    app_commands.Choice(name="🗺️ Cartes seulement",         value="maps"),
    app_commands.Choice(name="🚩🏛️ Drapeaux + Capitales",   value="flags,capitals"),
    app_commands.Choice(name="🚩🗺️ Drapeaux + Cartes",      value="flags,maps"),
    app_commands.Choice(name="🏛️🗺️ Capitales + Cartes",    value="capitals,maps"),
])
@app_commands.choices(difficulty=[
    app_commands.Choice(name="🟢 Facile  (pays très connus)",      value="easy"),
    app_commands.Choice(name="🟡 Moyen   (pays moyennement connus)", value="medium"),
    app_commands.Choice(name="🔴 Difficile (pays moins connus)",     value="hard"),
    app_commands.Choice(name="🌈 Tous les niveaux mélangés",         value="all"),
])
async def quiz_command(
    interaction: discord.Interaction,
    type: str = "all",
    difficulty: str = "easy",
    questions: app_commands.Range[int, 5, 20] = 10,
):
    channel_id = interaction.channel_id

    if quiz_mgr.is_active(channel_id):
        await interaction.response.send_message(
            "❌ Un quiz est déjà en cours dans ce salon !\n"
            "Utilisez `/stopquiz` pour l'arrêter.",
            ephemeral=True,
        )
        return

    q_types  = _TYPE_MAP.get(type, ["flag", "capital", "map"])
    type_lbl = _TYPE_LABELS.get(type, type)
    diff_lbl = _DIFF_LABELS.get(difficulty, difficulty)

    embed = discord.Embed(
        title="🌍 Quiz de Géographie",
        description=(
            f"**Type :** {type_lbl}\n"
            f"**Difficulté :** {diff_lbl}\n"
            f"**Questions :** {questions}\n\n"
            "Le quiz démarre dans **3 secondes…**\n"
            "Tout le monde peut répondre — chacun une fois par question !"
        ),
        color=0x3498DB,
    )
    await interaction.response.send_message(embed=embed)

    await asyncio.sleep(3)
    await quiz_mgr.start_quiz(interaction.channel, q_types, difficulty, questions)


@bot.tree.command(name="stopquiz", description="⏹️ Arrête le quiz en cours dans ce salon")
async def stopquiz_command(interaction: discord.Interaction):
    channel_id = interaction.channel_id

    if not quiz_mgr.is_active(channel_id):
        await interaction.response.send_message(
            "❌ Aucun quiz en cours dans ce salon.", ephemeral=True
        )
        return

    await interaction.response.send_message(
        embed=discord.Embed(
            title="⏹️ Quiz arrêté",
            description=f"Quiz interrompu par **{interaction.user.display_name}**.",
            color=0xE74C3C,
        )
    )
    await quiz_mgr.stop_quiz(channel_id)


@bot.tree.command(name="scores", description="🏆 Affiche les scores du quiz en cours")
async def scores_command(interaction: discord.Interaction):
    channel_id = interaction.channel_id

    if not quiz_mgr.is_active(channel_id):
        await interaction.response.send_message(
            "❌ Aucun quiz en cours dans ce salon.", ephemeral=True
        )
        return

    embed = quiz_mgr.get_scores_embed(channel_id)
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="aide", description="📖 Affiche l'aide du bot")
async def aide_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📖 Aide – Bot Quiz de Géographie",
        color=0x2ECC71,
    )
    embed.add_field(
        name="/quiz",
        value=(
            "Lance un quiz. Options :\n"
            "• **type** – drapeaux, capitales, cartes ou une combinaison\n"
            "• **difficulty** – facile / moyen / difficile / tous\n"
            "• **questions** – entre 5 et 20 questions"
        ),
        inline=False,
    )
    embed.add_field(name="/stopquiz", value="Arrête le quiz en cours.",    inline=False)
    embed.add_field(name="/scores",   value="Consulte les scores actuels.", inline=False)
    embed.add_field(
        name="Comment jouer ?",
        value=(
            "Chaque question affiche **4 boutons** (A/B/C/D).\n"
            "Cliquez sur votre réponse — vous avez **15 secondes** !\n"
            "Bonne réponse = **+1 point**. Tout le monde peut jouer simultanément."
        ),
        inline=False,
    )
    embed.set_footer(text="Bon quiz ! 🌍")
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ── Lancement ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not TOKEN:
        print(
            "❌  DISCORD_TOKEN non trouvé.\n"
            "   Copiez .env.example en .env et renseignez votre token."
        )
    else:
        bot.run(TOKEN)
