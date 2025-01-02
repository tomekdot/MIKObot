from collections import defaultdict
from discord.ext import commands, tasks
from discord import app_commands
import discord


class FAQCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api = bot.api

    @app_commands.command(name='youtube', description='link do yt MIKO')
    async def youtube(self, interaction: discord.Interaction):
        await interaction.response.send_message("https://www.youtube.com/@MIKO-math") ###Probably it should be fetched from the webpage?

    @app_commands.command(name='facebook', description='link do fb MIKO')
    async def youtube(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "https://www.facebook.com/koloolimpijskieMIKO")  ###Probably it should be fetched from the webpage?

    @app_commands.command(name='strona', description='link do strony MIKO')
    async def youtube(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "https://mikomath.org/")  ###Probably it should be fetched from the webpage?

    @app_commands.command(name='faq', description='link do strony MIKO')
    async def youtube(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "FAQ")  ###Probably it should be fetched from the webpage?


async def setup(bot):
    await bot.add_cog(FAQCommands(bot), guild=bot.guild)
