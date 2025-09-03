try:
    import discord
    from aiohttp.helpers import method_must_be_empty_body
    from discord.ext import commands, tasks
    DISCORD_AVAILABLE = True
except ImportError:
    discord = None
    commands = None
    tasks = None
    method_must_be_empty_body = None
    DISCORD_AVAILABLE = False

from utils import ClassMeet
import database_commands as db
import asyncio
import re
from datetime import datetime

async def add_class(ctx, bot):
    """
    Command to add a Discord class to the schedule.
    """
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    is_mod = any(role.name == "BotMod" for role in ctx.author.roles)

    if not is_mod:
        await ctx.send(f"You are not worthy, {ctx.author.mention}")
        return

    # Step 1: Ask for the Class day
    await ctx.send("Kiedy będzie koło? (podaj odpowiedź w formacie RRRR-MM-DD)")
    try:
        while True:
            meeting_date_msg = await bot.wait_for("message", check=check, timeout=30.0)
            try:
                datetime.strptime(meeting_date_msg.content, "%Y-%m-%d")
                meeting_date = meeting_date_msg.content
                break
            except ValueError:
                await ctx.send("Podaj poprawną datę w formacie RRRR-MM-DD.")
    except asyncio.TimeoutError:
        await ctx.send("Przekroczono limit czasu.")
        return

    # Step 2: Ask for the Class time
    await ctx.send("I od której do której? (HH:MM-HH:MM)")
    try:
        while True:
            meeting_time_msg = await bot.wait_for("message", check=check, timeout=30.0)
            pattern = r"^(\d{2}):(\d{2})-(\d{2}):(\d{2})$"
            match = re.fullmatch(pattern, meeting_time_msg.content)
            if match:
                h1, m1, h2, m2 = map(int, match.groups())
                if 0 <= h1 < 24 and 0 <= m1 < 60 and 0 <= h2 < 24 and 0 <= m2 < 60:
                    meeting_time = meeting_time_msg.content
                    break
            await ctx.send("Podaj poprawny czas w formacie HH:MM-HH:MM.")
    except asyncio.TimeoutError:
        await ctx.send("Przekroczono limit czasu.")
        return

    # Step 3: Ask for the Class type
    class_options = "\n".join([f"{key} - {value}" for key, value in ClassMeet.CLASS_TYPES.items()])
    await ctx.send(f"Jakie koło:\n{class_options}")
    try:
        while True:
            meeting_type_msg = await bot.wait_for("message", check=check, timeout=30.0)
            try:
                type_id = int(meeting_type_msg.content)
                if type_id in ClassMeet.CLASS_TYPES:
                    meeting_type = meeting_type_msg.content
                    break
            except ValueError:
                pass  # Let the message below handle it
            await ctx.send("Podaj poprawny typ (numer).")
    except asyncio.TimeoutError:
        await ctx.send("Przekroczono limit czasu.")
        return

    # Step 4: Ask for host
    await ctx.send("Kto prowadzi?")
    try:
        meeting_host_msg = await bot.wait_for("message", check=check, timeout=30.0)
        meeting_host = meeting_host_msg.content
    except asyncio.TimeoutError:
        await ctx.send("Przekroczono limit czasu.")
        return

    # Step 5: Ask for description
    await ctx.send("Jakiś opis?")
    try:
        meeting_description_msg = await bot.wait_for("message", check=check, timeout=30.0)
        meeting_description = meeting_description_msg.content
    except asyncio.TimeoutError:
        await ctx.send("Przekroczono limit czasu.")
        return

    # Summarize and save
    kolo = ClassMeet()
    kolo.load_from_discord(meeting_type, meeting_date, meeting_time, meeting_host, meeting_description)
    db.add_class(kolo)
    await ctx.send(f"Kółko '{kolo.type_str}' zostało ustawione na {kolo.date} o {kolo.time}.")

async def new_problem(ctx, bot):
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    await ctx.send("Podaj treść zadania:")
    try:
        problem_statement_msg = await bot.wait_for("message", check=check, timeout=600.0)
        statement_text = problem_statement_msg.content
        while True:
            msg = await ctx.send('Jeśli to cała treść, napisz "koniec". Jeśli nie, pisz dalej.')
            problem_statement_extra = await bot.wait_for("message", check=check, timeout=600.0)
            if problem_statement_extra.content.lower() == 'koniec':
                await msg.delete()
                await problem_statement_extra.delete()
                break
            statement_text += "\n" + problem_statement_extra.content
            await msg.delete()
    except asyncio.TimeoutError:
        await ctx.send("Przekroczono limit czasu.")
        return

    await ctx.send('Jeśli masz rozwiązanie, wklej je tutaj (użyj spoiler tagów `||`), jeśli nie, odpisz: "nie"')
    try:
        problem_solve_msg = await bot.wait_for("message", check=check, timeout=600.0)
        solve_text = ""
        if problem_solve_msg.content.lower() != 'nie':
            solve_text = problem_solve_msg.content
            while True:
                msg = await ctx.send('Jeśli to całe rozwiązanie, napisz "koniec". Jeśli nie, pisz dalej.')
                problem_solve_extra = await bot.wait_for("message", check=check, timeout=600.0)
                if problem_solve_extra.content.lower() == 'koniec':
                    await msg.delete()
                    await problem_solve_extra.delete()
                    break
                solve_text += "\n" + problem_solve_extra.content
                await msg.delete()
    except asyncio.TimeoutError:
        await ctx.send("Przekroczono limit czasu na podanie rozwiązania.")
        return

    await ctx.send("Jeśli chcesz dodać tagi (np. geometria, algebra), napisz je rozdzielając spacją:")
    try:
        tags_msg = await bot.wait_for("message", check=check, timeout=600.0)
        tags = tags_msg.content
    except asyncio.TimeoutError:
        await ctx.send("Przekroczono limit czasu na podanie tagów.")
        return

    problem_id = db.create_problem(statement_text, solve_text, tags=tags)
    await ctx.send(f"Dodano zadanie o ID: {problem_id}")
