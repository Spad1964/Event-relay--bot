import logging

import discord
from discord.ext import commands

log = logging.getLogger(__name__)

_MAX_FILES_PER_MESSAGE = 10


class MediaRelay(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or not message.attachments:
            return

        cfg = self.bot.config.media_relay
        if not cfg or message.channel.id not in cfg.source_channels:
            return

        target = self.bot.get_channel(cfg.target_channel_id)
        if target is None:
            log.warning("Media relay target channel %s not found", cfg.target_channel_id)
            return

        attachments = message.attachments[:_MAX_FILES_PER_MESSAGE]
        try:
            files = [await a.to_file() for a in attachments]
            await target.send(files=files)
        except discord.Forbidden:
            log.error("Missing permissions to relay media to channel %s", target.id)
        except discord.HTTPException as exc:
            log.error("HTTP error relaying media to channel %s: %s", target.id, exc)


async def setup(bot) -> None:
    await bot.add_cog(MediaRelay(bot))
