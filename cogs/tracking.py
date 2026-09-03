import time
import discord
from discord import app_commands
from discord.ext import commands

import database as db
from utils.image_card import create_stat_card


class Tracking(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.voice_sessions = {}  # (guild_id, user_id) -> start_time(time.time())

    @commands.Cog.listener()
    async def on_ready(self):
        # 봇 재시작 시 이미 음성채널에 있는 유저들의 세션을 새로 시작
        self.voice_sessions.clear()
        for guild in self.bot.guilds:
            afk_id = guild.afk_channel.id if guild.afk_channel else None
            for vc in guild.voice_channels:
                if vc.id == afk_id:
                    continue
                for member in vc.members:
                    if member.bot:
                        continue
                    self.voice_sessions[(guild.id, member.id)] = time.time()

    def _end_session(self, guild_id, user_id):
        key = (guild_id, user_id)
        start = self.voice_sessions.pop(key, None)
        if start is None:
            return 0
        return max(int(time.time() - start), 0)

    async def get_all_voice_totals(self, guild_id):
        """DB에 저장된 음성 시간 + 현재 접속 중인 세션의 실시간 시간을 합쳐서 반환"""
        rows = await db.get_all_users(guild_id)
        now = time.time()
        totals = {}
        for row in rows:
            total = row["voice_seconds"]
            key = (guild_id, row["user_id"])
            if key in self.voice_sessions:
                total += int(now - self.voice_sessions[key])
            totals[row["user_id"]] = total
        return totals

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot:
            return
        guild = member.guild
        afk_id = guild.afk_channel.id if guild.afk_channel else None

        before_valid = before.channel is not None and before.channel.id != afk_id
        after_valid = after.channel is not None and after.channel.id != afk_id

        if not before_valid and after_valid:
            self.voice_sessions[(guild.id, member.id)] = time.time()
        elif before_valid and not after_valid:
            elapsed = self._end_session(guild.id, member.id)
            if elapsed > 0:
                await db.add_voice_time(guild.id, member.id, elapsed)
        # 유효 채널 -> 유효 채널로 이동하는 경우는 세션 유지

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or message.guild is None:
            return
        await db.add_message(message.guild.id, message.author.id)

    @app_commands.command(name="음성", description="음성 채팅 누적 시간을 확인합니다")
    @app_commands.describe(유저="확인할 유저 (비워두면 본인)")
    async def voice_stat(self, interaction: discord.Interaction, 유저: discord.Member = None):
        await interaction.response.defer()
        member = 유저 or interaction.user

        await db.get_user(interaction.guild.id, member.id)  # 유저 레코드 보장
        totals = await self.get_all_voice_totals(interaction.guild.id)
        total_seconds = totals.get(member.id, 0)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60

        sorted_ids = sorted(totals.keys(), key=lambda uid: totals[uid], reverse=True)
        rank = sorted_ids.index(member.id) + 1 if member.id in sorted_ids else len(sorted_ids) + 1
        total = len(sorted_ids)

        file = await create_stat_card(
            member, "음성 누적 시간",
            f"{hours}시간 {minutes}분",
            f"서버 음성 순위 {rank}위 / {total}명 중"
        )
        await interaction.followup.send(file=file)

    @app_commands.command(name="채팅", description="채팅 누적 횟수를 확인합니다")
    @app_commands.describe(유저="확인할 유저 (비워두면 본인)")
    async def chat_stat(self, interaction: discord.Interaction, 유저: discord.Member = None):
        await interaction.response.defer()
        member = 유저 or interaction.user

        row = await db.get_user(interaction.guild.id, member.id)
        rank, total = await db.get_chat_rank(interaction.guild.id, member.id)
        file = await create_stat_card(
            member, "채팅 누적 횟수",
            f"{row['message_count']:,}회",
            f"서버 채팅 순위 {rank}위 / {total}명 중"
        )
        await interaction.followup.send(file=file)


async def setup(bot):
    await bot.add_cog(Tracking(bot))
