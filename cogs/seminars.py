import os
import zoneinfo
from aiohttp.client_exceptions import ClientResponseError
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Literal
from babel.dates import format_datetime
import discord
from discord import app_commands
from discord.ext import commands, tasks
from utils.models import Seminar
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from utils.forms_api import create_from_template
from zoneinfo import ZoneInfo

class SeminarCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api = bot.api
        self.scheduler = AsyncIOScheduler()
        self.scheduler.start()
        self.scheduled_seminars=[]
        self.started_seminars = []
        self.ended_seminars = []
        self.update_seminars.start()

    @staticmethod
    async def _short_seminar_description(self, seminar: Seminar):
        time_format = lambda t: format_datetime(t, 'HH:mm', locale=os.getenv('LOCALE'))
        featured_icon = ':star:' if seminar.featured else ''
        special_guest_icon = ':bust_in_silhouette:' if seminar.special_guest else ''
        group = f'<@&{seminar.group_role_id}>' if seminar.group_role_id else seminar.group_name or ''
        tutors = f'Prowadzący: { ', '.join(seminar.tutors)}' if seminar.tutors else ''

        line1 = f'`{time_format(seminar.start)}` **{seminar.theme}** {featured_icon}{special_guest_icon}'
        line2 = f' {group}{tutors}'

        return f'{line1}\n{line2.strip(' ')}' if not line2.isspace() else line1

    @app_commands.command(name='upcoming', description='Wyświetl nadchodzące zajęcia')
    async def upcoming(self, interaction: discord.Interaction, filter: Literal['all', 'my'] = 'all'):
        seminars = await self.api.fetch_seminars(start_date=datetime.now().date(),
                                                 end_date=(datetime.now() + timedelta(weeks=2)).date())
        if filter == 'my':
            user_role_ids = [str(role.id) for role in interaction.user.roles]
            seminars = [seminar for seminar in seminars if seminar.group_role_id in user_role_ids]

        seminars_by_day = defaultdict(list)
        for seminar in seminars:
            seminars_by_day[seminar.start.date()].append(seminar)

        title = 'Nadchodzące zajęcia:' if filter == 'all' else 'Nadchodzące zajęcia dla Ciebie:'
        embed = discord.Embed(title=title, color=int(os.getenv('MIKO_BLUE'), 16))

        date_format = lambda d: format_datetime(d, 'EEEE, d MMMM:', locale=os.getenv('LOCALE'))

        for date, seminars in sorted(seminars_by_day.items())[:5]:
            formatted_seminars = '\n'.join([
                await self._short_seminar_description(seminar)
                for seminar in sorted(seminars, key=lambda s: s.start)
            ])
            embed.add_field(name=date_format(date), value=formatted_seminars, inline=False)

        if not embed.fields:
            embed.description = 'Brak eventów :sob: \nSprawdź ponownie później.'

        await interaction.response.send_message(embed=embed)

    @staticmethod
    async def seminar_embed(self, seminar: Seminar):
        """Function, that returns embed object with info about seminar"""
        embed = discord.Embed(title=seminar.theme, color=int(os.getenv('MIKO_BLUE'), 16))

        embed.add_field(name='Data i godzina',
                        value=format_datetime(seminar.start, 'd MMMM HH:mm', locale=os.getenv('LOCALE')))
        embed.add_field(name='Trudność', value=seminar.difficulty_label)
        embed.add_field(name='Opis', value=seminar.description, inline=False)
        if seminar.tutors:
            embed.add_field(name='Prowadzący', value=', '.join(seminar.tutors), inline=False)
        return embed

    @app_commands.command(name='seminar', description='Wyświetl szczegóły zajęć')
    async def seminar(self, interaction: discord.Interaction, seminar_id: int):
        try:
            seminar = await self.api.fetch_seminar(seminar_id)
        except ClientResponseError as e:
            if e.status == 404:
                embed = discord.Embed(title='Nie istnieje!',
                                      description='Nie znaleziono zajęć o takim ID :anguished:',
                                      color=int(os.getenv('MIKO_RED'), 16))
                return await interaction.response.send_message(embed=embed, ephemeral=True)
            raise
        embed = await self.seminar_embed(seminar)
        await interaction.response.send_message(embed=embed)

    async def cog_app_command_error(self, interaction, error):
        if isinstance(error, app_commands.CommandInvokeError) and isinstance(error.original, ClientResponseError):
            embed = discord.Embed(title='Okropny błąd!',
                                  description=f'Chwilowo nie mam dostępu do danych (`{error.original.status}`). Spróbuj ponownie później lub samodzielnie sprawdź na [stronie internetowej](https://mikomath.org/kolo).',
                                  color=int(os.getenv('MIKO_RED'), 16))
            embed.set_author(name='mikomath.org/kolo', url='https://mikomath.org/kolo')
            return await interaction.response.send_message(embed=embed)
        else:
            raise error

    async def get_role(self, role_id):
        """returns role object, from role id"""
        guild = self.bot.get_guild(self.bot.guild.id)
        if not guild:
            guild = await self.bot.fetch_guild(self.bot.guild.id)
        role = guild.get_role(role_id)
        return role

    async def get_channel(self, channel_id):
        """returns channel object, from channel id"""
        channel = self.bot.get_channel(channel_id)
        if not channel:
            channel = await self.bot.fetch_channel(channel_id)
        return channel

    @tasks.loop(seconds=15)###seconds for debug, in prod should be minutes
    async def update_seminars(self):
        """Function check for new seminars in near future, to add them to the scheduler."""
        print("PERFORMING LOOP TASK")
        reminders = await self.api.fetch_next_reminder()
        print (reminders)
        for reminder in reminders:
            if(datetime.fromisoformat(reminder['date_time'])-datetime.now(zoneinfo.ZoneInfo("Europe/Warsaw")))<=timedelta(seconds=15) and not reminder['pinged']:
                seminar_to_ping = await self.api.fetch_seminar(reminder['seminar'])
                if reminder['type']== "invite":
                    await self.schedule_start_message(seminar_to_ping)
                elif reminder['type']== "feedback":
                    await self.schedule_end_message(seminar_to_ping)
                await self.api.mark_reminder_as_pinged(reminder['id'])

    async def schedule_start_message(self, seminar: Seminar):
        target_time=seminar.start - timedelta(hours=1)
        self.scheduler.add_job(
            self.send_invite_to_seminar,
            DateTrigger(run_date=target_time),
            args=[seminar.discord_channel_id,seminar],  # Arguments for the function
        )

    async def schedule_end_message(self, seminar: Seminar):
        target_time = seminar.start + seminar.duration
        if seminar.group_role_id:   role = await self.get_role(int(seminar.group_role_id))
        self.scheduler.add_job(
            self.send_request_for_feedback,
            DateTrigger(run_date=target_time),
            args=[seminar.discord_channel_id, seminar],  # Arguments for the function
        )

    async def send_request_for_feedback(self, channel_id: int, seminar: Seminar):
        """Sends request for feedback on seminar channel"""
        if seminar.group_role_id:   role = await self.get_role(int(seminar.group_role_id))
        if channel_id: channel_id = int(channel_id)
        channel = await self.get_channel(channel_id)
        feedback_template = await self.api.fetch_template(seminar.form)
        feedback_link, edit_link= await create_from_template(feedback_template,f"Feedback {seminar.theme}")
        try:
            if role:
                await channel.send(f"Dziękujemy za kółko {role.mention} i prosimy o feedback {feedback_link} ! ")
            else:
                await channel.send(f"Dziękujemy za kółko i prosimy o feedback {feedback_link} ! ")
        except Exception as e:
            print("ERROR while sending feedback: ", e)

    async def send_invite_to_seminar(self, channel_id, seminar: Seminar):
        """Sends invitation to seminar on seminar channel, with info about it as embed"""
        if seminar.group_role_id:   role = await self.get_role(int(seminar.group_role_id))
        if channel_id: channel_id = int(channel_id)
        channel = await self.get_channel(channel_id)
        try:
            if role:
                await channel.send(f"Zapraszamy na kółko! {role.mention}")
            else:
                await channel.send(f"Zapraszamy na kółko!")
            embed = await self.seminar_embed(self,seminar)
            await channel.send(embed=embed)
        except Exception as e:
            print("ERROR while sending invite: ", e)
    def cog_unload(self):
        self.scheduler.shutdown()

async def setup(bot):
    await bot.add_cog(SeminarCommands(bot), guild=bot.guild)
