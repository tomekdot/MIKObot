from collections import defaultdict
from discord.ext import commands, tasks
from discord import app_commands
import discord


class PollButton(discord.ui.Button):
    def __init__(self, label, poll_view):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.poll_view = poll_view

    async def callback(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        # Prevent double voting
        if user_id in self.poll_view.votes:
            await interaction.response.send_message("Już zagłosowałeś!", ephemeral=True)
            return
        # Record vote
        self.poll_view.votes[user_id] = self.label
        self.poll_view.option_counts[self.label] += 1

        await interaction.response.send_message(
            f"Dziękujemy za głos! **{self.label}**.", ephemeral=True
        )


class AnonymousPollView(discord.ui.View):
    def __init__(self, poll_question, poll_options, timeout=60):
        super().__init__(timeout=timeout)
        self.poll_question = poll_question
        self.poll_options = poll_options
        self.votes = defaultdict(list)  # Store votes anonymously
        self.option_counts = {option: 0 for option in poll_options}  # Track vote counts

        for option in poll_options:
            self.add_item(PollButton(option, self))

    async def end_poll(self, interaction: discord.Interaction):
        # Build results embed
        results = [f"**{option}**: {count} głosów" for option, count in self.option_counts.items()]
        embed = discord.Embed(
            title="Wyniki",
            description=f"**{self.poll_question}**\n\n" + "\n".join(results),
            color=discord.Color.green(),
        )
        await interaction.channel.send(embed=embed)
        self.stop()


class TutorCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api = bot.api

    @app_commands.command(name="czy_rozumiemy", description="Creates simple pool")
    async def BinaryPool(self, interaction: discord.Interaction, question: str, time: int):
        embed = discord.Embed(
            title="Ankieta",
            description=f"**{question}**\n\n" + "\n".join(f"• {opt}" for opt in ['tak','nie']),
            color=discord.Color.blue(),
        )
        embed.set_footer(text="Naciśnij, żeby zagłosować!")
        view = AnonymousPollView(question, ['tak','nie'],timeout=time)
        await interaction.response.send_message(embed=embed, view=view)
        await view.wait()
        if view.is_finished():
            await view.end_poll(interaction)

    @app_commands.command(name="ankieta", description="Creates simple pool with custom options")
    async def Pool(self, interaction: discord.Interaction, question: str,options: str, time: int):
        poll_options = [opt.strip() for opt in options.split(",")]
        embed = discord.Embed(
            title="Ankieta",
            description=f"**{question}**\n\n" + "\n".join(f"• {opt}" for opt in poll_options),
            color=discord.Color.blue(),
        )
        embed.set_footer(text="Naciśnij, żeby zagłosować!")
        view = AnonymousPollView(question, poll_options,timeout=time)
        await interaction.response.send_message(embed=embed, view=view)
        await view.wait()
        if view.is_finished():
            await view.end_poll(interaction)

    @app_commands.command(name="nie_rozumiem", description="Użyj, jeśli nie rozumiesz czegoś na wykładzie")
    @discord.app_commands.checks.cooldown(rate=1, per=300.0, key=lambda i: (i.user.id))
    async def i_dont_understand(self, interaction: discord.Interaction,czego_nie_rozumiem: str):
        await interaction.response.send_message("Przekazaliśmy informację!", ephemeral=True)
        await interaction.channel.send(f"Ktoś nie rozumie {czego_nie_rozumiem}!")

    @i_dont_understand.error
    async def i_dont_understand_error(self, interaction: discord.Interaction, error):
        if isinstance(error, discord.app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"Komenda jest na cooldownie. Spróbuj za {error.retry_after:.2f} sekund.",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(TutorCommands(bot), guild=bot.guild)
