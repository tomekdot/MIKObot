import os
from dotenv import load_dotenv
from aiohttp import ClientSession, ClientTimeout
import discord
from discord.ext import commands
from utils.api import ApiWrapper

dotenv_path = os.path.join(os.path.dirname(__file__), 'config.env')
load_dotenv(dotenv_path=dotenv_path)


class MIKOBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(command_prefix=commands.when_mentioned_or('!'), intents=discord.Intents.all())
        self.guild = discord.Object(id=os.getenv('MIKO_GUILD_ID'))
        self.api_session = None
        self.api = ApiWrapper()

    async def setup_api_session(self):
        self.api_session = ClientSession(
            headers={'Authorization': f'Token {os.getenv("MIKO_API_TOKEN")}'},
            base_url=os.getenv('MIKO_API_URL'),
            timeout=ClientTimeout(total=30),
            raise_for_status=True,
        )
        await self.api.setup(self.api_session)

    async def setup_hook(self):
        print('Loading cogs...')
        for filename in os.listdir('./cogs'):
            name, extension = os.path.splitext(filename)
            if name.startswith('_') or extension != '.py':
                continue

            try:
                await self.load_extension(f'cogs.{name}')
            except Exception as e:
                print(f'\tfailed to load {filename}: {e}')
            else:
                print(f'\tloaded {filename}')
        await self.setup_api_session()

    async def on_ready(self):
        await bot.tree.sync(guild=self.guild)
        print(f'Bot ready, logged in as {self.user} ({self.user.id})')


bot = MIKOBot()

if __name__ == '__main__':
    bot.run(os.getenv('DISCORD_TOKEN'))
