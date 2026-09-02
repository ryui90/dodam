import discord
from discord import app_commands
from discord.ext import commands

import database as db
from config import COLOR_MAIN


def parse_color(color_str):
    if not color_str:
        return COLOR_MAIN
    try:
        return int(color_str.replace("#", ""), 16)
    except ValueError:
        return COLOR_MAIN


class ShopButton(discord.ui.Button):
    def __init__(self, guild_id: int, role_id: int, price: int, label: str):
        super().__init__(
            label=f"{label} ({price:,}P)",
            style=discord.ButtonStyle.success,
            custom_id=f"shop_buy:{guild_id}:{role_id}",
        )
        self.role_id = role_id

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        role = guild.get_role(self.role_id)
        if role is None:
            await interaction.response.send_message("이 역할은 더 이상 존재하지 않습니다.", ephemeral=True)
            return
        if role in interaction.user.roles:
            await interaction.response.send_message("이미 보유하고 있는 역할입니다.", ephemeral=True)
            return

        price = await db.get_shop_price(guild.id, self.role_id)
        if price is None:
            await interaction.response.send_message("이 역할은 더 이상 상점에서 판매하지 않습니다.", ephemeral=True)
            return

        row = await db.get_user(guild.id, interaction.user.id)
        if row["points"] < price:
            await interaction.response.send_message(
                f"포인트가 부족합니다. (보유: {row['points']:,}P / 필요: {price:,}P)", ephemeral=True
            )
            return

        await db.add_points(guild.id, interaction.user.id, -price)
        try:
            await interaction.user.add_roles(role, reason="포인트 상점 구매")
        except discord.Forbidden:
            await db.add_points(guild.id, interaction.user.id, price)
            await interaction.response.send_message(
                "역할을 지급할 권한이 없어 구매가 취소되었습니다.", ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"🎉 {role.mention} 역할을 구매했습니다! (-{price:,}P)", ephemeral=True
        )


class ShopView(discord.ui.View):
    def __init__(self, guild_id: int, roles_data):
        super().__init__(timeout=None)
        for role_id, price, label in roles_data:
            self.add_item(ShopButton(guild_id, role_id, price, label))


class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def register_persistent_views(self):
        """봇 재시작 후에도 기존에 보낸 상점 메세지의 버튼이 동작하도록 뷰를 재등록"""
        for guild in self.bot.guilds:
            rows = await db.get_shop_roles(guild.id)
            if not rows:
                continue
            roles_data = []
            for r in rows:
                role = guild.get_role(r["role_id"])
                label = role.name if role else "알 수 없는 역할"
                roles_data.append((r["role_id"], r["price"], label))
            if roles_data:
                self.bot.add_view(ShopView(guild.id, roles_data))

    @app_commands.command(name="상점역할", description="[관리자] 포인트 상점에 판매할 역할을 등록합니다")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(역할="상점에 등록할 역할", 포인트="구매에 필요한 포인트")
    async def add_shop_role(self, interaction: discord.Interaction, 역할: discord.Role, 포인트: int):
        if 포인트 <= 0:
            await interaction.response.send_message("1 이상의 값을 입력해주세요.", ephemeral=True)
            return
        await db.upsert_shop_role(interaction.guild.id, 역할.id, 포인트)
        await interaction.response.send_message(
            f"✅ {역할.mention} 역할이 {포인트:,}P로 상점에 등록되었습니다.\n"
            f"`/상점메세지`로 상점 메세지를 새로 보내면 버튼에 반영됩니다.",
            ephemeral=True,
        )

    @app_commands.command(name="상점메세지", description="포인트 상점 임베드 메세지를 보냅니다")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(
        채널="메세지를 보낼 채널", 제목="임베드 제목", 내용="임베드 내용",
        색상="16진수 색상 코드, 생략 가능"
    )
    async def shop_message(self, interaction: discord.Interaction, 채널: discord.TextChannel,
                            제목: str, 내용: str, 색상: str = None):
        rows = await db.get_shop_roles(interaction.guild.id)
        if not rows:
            await interaction.response.send_message(
                "등록된 상점 역할이 없습니다. 먼저 `/상점역할`로 역할을 등록해주세요.", ephemeral=True
            )
            return

        roles_data = []
        for r in rows:
            role = interaction.guild.get_role(r["role_id"])
            if role:
                roles_data.append((r["role_id"], r["price"], role.name))

        embed = discord.Embed(title=제목, description=내용, color=parse_color(색상))
        view = ShopView(interaction.guild.id, roles_data)
        self.bot.add_view(view)
        await 채널.send(embed=embed, view=view)
        await interaction.response.send_message("✅ 상점 메세지를 보냈습니다.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Shop(bot))
