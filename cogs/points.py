import discord
from discord import app_commands
from discord.ext import commands

import database as db
from config import COLOR_MAIN


class Points(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="포인트", description="누적 포인트를 확인합니다")
    @app_commands.describe(유저="확인할 유저 (비워두면 본인)")
    async def points(self, interaction: discord.Interaction, 유저: discord.Member = None):
        member = 유저 or interaction.user
        row = await db.get_user(interaction.guild.id, member.id)
        embed = discord.Embed(title="💰 포인트 현황", color=COLOR_MAIN)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.description = f"**{member.display_name}**님의 포인트: **{row['points']:,} P**"
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="추가", description="[관리자] 유저에게 포인트를 지급합니다")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(유저="포인트를 지급할 유저", 포인트="지급할 포인트")
    async def add_points(self, interaction: discord.Interaction, 유저: discord.Member, 포인트: int):
        if 포인트 <= 0:
            await interaction.response.send_message("1 이상의 값을 입력해주세요.", ephemeral=True)
            return
        await db.add_points(interaction.guild.id, 유저.id, 포인트)
        row = await db.get_user(interaction.guild.id, 유저.id)
        await interaction.response.send_message(
            f"✅ {유저.mention}님에게 {포인트:,}P를 지급했습니다. (현재 {row['points']:,}P)", ephemeral=True
        )

    @app_commands.command(name="제거", description="[관리자] 유저의 포인트를 차감합니다")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(유저="포인트를 차감할 유저", 포인트="차감할 포인트")
    async def remove_points(self, interaction: discord.Interaction, 유저: discord.Member, 포인트: int):
        if 포인트 <= 0:
            await interaction.response.send_message("1 이상의 값을 입력해주세요.", ephemeral=True)
            return
        await db.add_points(interaction.guild.id, 유저.id, -포인트)
        row = await db.get_user(interaction.guild.id, 유저.id)
        await interaction.response.send_message(
            f"✅ {유저.mention}님의 포인트에서 {포인트:,}P를 차감했습니다. (현재 {row['points']:,}P)", ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(Points(bot))
