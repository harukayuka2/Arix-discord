from dotenv import load_dotenv
import os
import discord
import asyncio
import json
from datetime import datetime, timezone
import re
import pytz
from pathlib import Path
from discord.ext import commands
import gemini_client

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")


@bot.event
async def on_message(message: discord.Message):
    """Handle messages that mention or reply to the bot.

    If a user mentions the bot or replies to a bot message, treat the
    message content as a question and forward it to Gemini, then reply
    and append to history.json.
    """
    # Ignore messages from bots (including ourselves)
    if message.author.bot:
        return

    invoked = False
    content = message.content or ""

    # Check if message is a reply to a bot message
    if message.reference and getattr(message.reference, "message_id", None):
        try:
            ref_msg = await message.channel.fetch_message(message.reference.message_id)
            if ref_msg and ref_msg.author and ref_msg.author.id == bot.user.id:
                invoked = True
        except Exception:
            invoked = False

    # Or check if the bot was mentioned
    if not invoked and bot.user in message.mentions:
        invoked = True

    if invoked:
        # Strip mention tokens from content
        content = content.replace(f"<@{bot.user.id}>", "").replace(f"<@!{bot.user.id}>", "").strip()
        if not content:
            # Nothing to ask
            return

        try:
            q = _maybe_inject_time_info(content)
            async with message.channel.typing():
                reply = await asyncio.to_thread(
                    gemini_client.generate_text,
                    q,
                    max_output_tokens=512,
                    personality="menjawab 50-250 kata saja",
                )

            if not reply:
                reply = "(no response from Gemini)"
            if len(reply) > 1990:
                reply = reply[:1990] + "..."

            ts_user = datetime.now(timezone.utc).isoformat()
            ts_bot = datetime.now(timezone.utc).isoformat()
            entries = [
                {"role": "user", "content": content, "timestamp": ts_user, "message_id": getattr(message, "id", None)},
                {"role": "bot", "content": reply, "timestamp": ts_bot},
            ]
            _append_history(entries)

            # Reply and mention the user (explicit allowed_mentions)
            try:
                await message.reply(reply, mention_author=True, allowed_mentions=discord.AllowedMentions(replied_user=True))
            except Exception:
                await message.channel.send(f"{message.author.mention} {reply}", allowed_mentions=discord.AllowedMentions(users=[message.author.id]))
        except Exception as e:
            try:
                await message.channel.send(f"Error contacting Gemini: {e}", allowed_mentions=discord.AllowedMentions(users=[message.author.id]))
            except Exception:
                pass

    # Allow commands to be processed as well
    await bot.process_commands(message)


@bot.command(name="ping")
async def ping(ctx):
    """Responds with Pong! and latency."""
    latency_ms = round(bot.latency * 1000)
    await ctx.send(f"Pong! {latency_ms}ms")


@bot.command(name="hello")
async def hello(ctx):
    """Greets the user."""
    await ctx.send(f"Hello, {ctx.author.mention}!")


HISTORY_PATH = Path("history.json")


def _append_history(entries: list) -> None:
    try:
        if HISTORY_PATH.exists():
            with HISTORY_PATH.open("r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = []
    except Exception:
        data = []

    data.extend(entries)
    try:
        with HISTORY_PATH.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Failed to write history.json:", e)


def _is_time_query(text: str) -> bool:
    if not text:
        return False
    if re.search(r"\b(jam|waktu|pukul|time)\b", text, re.IGNORECASE):
        return True
    if re.search(r"\b\d{1,2}:\d{2}\b", text):
        return True
    return False


def _maybe_inject_time_info(text: str) -> str:
    if not _is_time_query(text):
        return text

    now_utc = datetime.now(timezone.utc)
    tz_names = ["UTC", "Asia/Jakarta"]
    times = []
    for tz in tz_names:
        try:
            local = now_utc.astimezone(pytz.timezone(tz))
            times.append(f"{tz}: {local.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        except Exception:
            pass

    if times:
        header = "Current server times: " + ", ".join(times) + "\n\n"
        return header + text
    return text


@bot.command(name="ask")
async def ask(ctx, *, question: str):
    """Ask Google Gemini Flash 2.5 and return its reply."""
    try:
        q = _maybe_inject_time_info(question)
        async with ctx.typing():
            # Run blocking Gemini call in a thread to avoid blocking the event loop
            reply = await asyncio.to_thread(
                gemini_client.generate_text,
                q,
                max_output_tokens=512,
                personality="menjawab 50-250 kata saja",
            )
        if not reply:
            reply = "(no response from Gemini)"
        # Truncate to avoid exceeding Discord message limits
        if len(reply) > 1990:
            reply = reply[:1990] + "..."

        # Append to history
        ts_user = datetime.now(timezone.utc).isoformat()
        ts_bot = datetime.now(timezone.utc).isoformat()
        entries = [
            {"role": "user", "content": question, "timestamp": ts_user, "message_id": getattr(ctx.message, "id", None)},
            {"role": "bot", "content": reply, "timestamp": ts_bot},
        ]
        _append_history(entries)

        # Reply to the user's message and mention them (explicit allowed_mentions)
        try:
            await ctx.message.reply(reply, mention_author=True, allowed_mentions=discord.AllowedMentions(replied_user=True))
        except Exception:
            # Fallback: send a plain message that mentions the user
            await ctx.send(f"{ctx.author.mention} {reply}", allowed_mentions=discord.AllowedMentions(users=[ctx.author.id]))
    except Exception as e:
        await ctx.send(f"Error contacting Gemini: {e}")


@bot.command(name="askp")
async def askp(ctx, persona: str, *, question: str):
    """Ask Gemini with a persona. Usage: `!askp <persona> <question>`"""
    try:
        q = _maybe_inject_time_info(question)
        persona_full = f"{persona}. menjawab 50-250 kata saja"
        async with ctx.typing():
            reply = await asyncio.to_thread(
                gemini_client.generate_text,
                q,
                max_output_tokens=512,
                personality=persona_full,
            )
        if not reply:
            reply = "(no response from Gemini)"
        if len(reply) > 1990:
            reply = reply[:1990] + "..."

        ts_user = datetime.now(timezone.utc).isoformat()
        ts_bot = datetime.now(timezone.utc).isoformat()
        entries = [
            {"role": "user", "content": question, "timestamp": ts_user, "persona": persona, "message_id": getattr(ctx.message, "id", None)},
            {"role": "bot", "content": reply, "timestamp": ts_bot, "persona": persona},
        ]
        _append_history(entries)

        try:
            await ctx.message.reply(reply, mention_author=True, allowed_mentions=discord.AllowedMentions(replied_user=True))
        except Exception:
            await ctx.send(f"{ctx.author.mention} {reply}", allowed_mentions=discord.AllowedMentions(users=[ctx.author.id]))
    except Exception as e:
        await ctx.send(f"Error contacting Gemini: {e}")


if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("DISCORD_TOKEN not set. See README.md and .env.example")
    bot.run(TOKEN)
