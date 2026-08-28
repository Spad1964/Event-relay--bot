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
        if message.author.bot:
            return

        attachments = list(message.attachments)
        for snapshot in message.message_snapshots:
            attachments.extend(snapshot.attachments)
        if not attachments:
            return

        cfg = self.bot.config.media_relay
        if not cfg or message.channel.id not in cfg.source_channels:
            return

        target = self.bot.get_channel(cfg.target_channel_id)
        if target is None:
            log.warning("Media relay target channel %s not found", cfg.target_channel_id)
            return

        if len(attachments) > _MAX_FILES_PER_MESSAGE:
            log.info(
                "Message %s in channel %s has %d attachments; relaying first %d",
                message.id,
                message.channel.id,
                len(attachments),
                _MAX_FILES_PER_MESSAGE,
            )
        attachments = attachments[:_MAX_FILES_PER_MESSAGE]

        limit = target.guild.filesize_limit
        small = [a for a in attachments if a.size <= limit]
        large = [a for a in attachments if a.size > limit]

        log.info(
            "Relaying msg %s from %s (channel %s) to channel %s: %d uploadable, %d over %d-byte limit (link fallback)",
            message.id,
            message.author,
            message.channel.id,
            target.id,
            len(small),
            len(large),
            limit,
        )

        try:
            batch: list[discord.Attachment] = []
            batch_size = 0
            for a in small:
                if batch and (len(batch) >= _MAX_FILES_PER_MESSAGE or batch_size + a.size > limit):
                    await target.send(files=[await f.to_file() for f in batch])
                    batch, batch_size = [], 0
                batch.append(a)
                batch_size += a.size
            if batch:
                await target.send(files=[await f.to_file() for f in batch])

            for a in large:
                log.info(
                    "Attachment %s (%d bytes) exceeds target limit; relaying as link instead of re-upload",
                    a.filename,
                    a.size,
                )
                await target.send(content=a.url)

            log.info("Relayed msg %s to channel %s", message.id, target.id)
        except discord.Forbidden:
            log.error("Missing permissions to relay media to channel %s", target.id)
        except discord.HTTPException as exc:
            log.error("HTTP error relaying media to channel %s: %s", target.id, exc)


async def setup(bot) -> None:
    await bot.add_cog(MediaRelay(bot))
