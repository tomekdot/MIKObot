import os
import sys

try:
    import discord
    from discord.ext import commands, tasks
    DISCORD_AVAILABLE = True
except ImportError:
    discord = None
    commands = None
    tasks = None
    DISCORD_AVAILABLE = False

import bot_commands
import database_commands as db
from utils import user_class_match

# --- Configuration ---
# You can change this to the name of your Discord server (guild)
TARGET_GUILD_NAME = os.environ.get("TARGET_GUILD", "TestServer")

def main():
    """Main function to setup and run the Discord bot."""
    if not DISCORD_AVAILABLE:
        print("Discord.py is not installed. Please install dependencies from requirements.txt.", file=sys.stderr)
        sys.exit(1)

    # --- Bot Initialization ---
    intents = discord.Intents.all()
    bot = commands.Bot(command_prefix="!", intents=intents)

    # --- Helper Functions ---
    async def format_and_send_classes(ctx, classes_list):
        """Helper function to format and send a list of classes."""
        if not classes_list:
            await ctx.send("Brak zaplanowanych kół w najbliższym czasie.")
            return
        
        response = ""
        for i, class_meet in enumerate(classes_list, 1):
            response_part = (
                f"**{i}: Koło z {class_meet.type_str}**\n"
                f"> Data: {class_meet.date} w godzinach: {class_meet.time}\n"
                f"> Prowadzi: {class_meet.host}\n"
                f"> Opis: {class_meet.description}\n\n"
            )
            # Discord has a 2000 character limit per message
            if len(response) + len(response_part) > 2000:
                await ctx.send(response)
                response = ""
            response += response_part
        
        if response:
            await ctx.send(response)

    # --- Bot Commands ---
    @bot.command(name="SetClass", aliases=["UstawKolo", "UstawKoło", "UstawKlase", "UstawKlasę"])
    @commands.has_role("BotMod")
    async def set_class(ctx):
        """Starts a dialog to schedule a new class. (Moderator only)"""
        await bot_commands.add_class(ctx, bot)

    @bot.command(name="Classes", aliases=["Kola", "Koła"])
    async def list_classes(ctx):
        """Lists all upcoming classes."""
        all_classes = db.get_class()
        await format_and_send_classes(ctx, all_classes)

    @bot.command(name="MyClasses", aliases=["MojeKola", "MojeKoła", "MojeKlasy"])
    async def list_my_classes(ctx):
        """Lists upcoming classes that match the user's roles."""
        all_classes = db.get_class()
        matched_classes = [c for c in all_classes if user_class_match(c.type, ctx.author.roles)]
        if not matched_classes:
            await ctx.send("Nie znaleziono kół pasujących do twoich ról.")
            return
        await format_and_send_classes(ctx, matched_classes)

    @bot.command(name="NewProblem", aliases=["NoweZadanie"])
    @commands.has_role("BotMod")
    async def new_problem(ctx):
        """Starts a dialog to add a new problem. (Moderator only)"""
        await bot_commands.new_problem(ctx, bot)

    @bot.command()
    async def ping(ctx):
        """Checks if the bot is responsive."""
        await ctx.send(f"Pong, {ctx.author.name}!")

    # --- Bot Events ---
    @bot.event
    async def on_ready():
        """Called when the bot is ready and connected to Discord."""
        print(f'Bot is ready. Logged in as {bot.user}')
        db.connect_database()
        if not hourly_task.is_running():
            hourly_task.start()

    @tasks.loop(hours=1)
    async def hourly_task():
        """A background task that runs every hour to sync members."""
        print("Hourly task: Syncing members...")
        target_guild = discord.utils.get(bot.guilds, name=TARGET_GUILD_NAME)
        if target_guild:
            db.sync_members(target_guild.members)
            print(f"Member sync complete for guild: {target_guild.name}")
        else:
            print(f"Could not find the target guild '{TARGET_GUILD_NAME}'.", file=sys.stderr)

    @bot.event
    async def on_message(message: discord.Message):  # type: ignore
        """Called for every message sent in a channel the bot can see."""
        if message.author.bot:
            return

        # Awarding points for every message can be exploited.
        # Consider adding a cooldown or awarding points for specific actions.
        db.add_point(message.author, 1)
        
        await bot.process_commands(message)

    @bot.event
    async def on_reaction_add(reaction: discord.Reaction, user: discord.User):  # type: ignore
        """Called when a user adds a reaction to a message."""
        if user.bot:
            return
        # Award points to the author of the message that got a reaction
        db.add_point(reaction.message.author, 1)

    @bot.event
    async def on_reaction_remove(reaction: discord.Reaction, user: discord.User):  # type: ignore
        """Called when a user removes a reaction from a message."""
        if user.bot:
            return
        db.add_point(reaction.message.author, -1)

    @bot.event
    async def on_member_join(member: discord.Member):  # type: ignore
        """Called when a new member joins the server."""
        print(f"New member joined: {member.name}")
        db.add_member(member)

    @bot.event
    async def on_member_remove(member: discord.Member):  # type: ignore
        """Called when a member leaves or is removed from the server."""
        print(f"Member left: {member.name}")
        db.remove_member(member)
        
    @bot.event
    async def on_command_error(ctx, error):
        """Handles errors for bot commands."""
        if isinstance(error, commands.MissingRole):
            await ctx.send("Nie masz uprawnień do użycia tej komendy.")
        else:
            print(f"An error occurred: {error}", file=sys.stderr)


    # --- Run Bot ---
    try:
        with open("token.txt", "r") as f:
            token = f.read().strip()
        if not token:
            raise FileNotFoundError
        bot.run(token)
    except FileNotFoundError:
        print("Bot token not found. Please create a 'token.txt' file with your bot token.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred while running the bot: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
