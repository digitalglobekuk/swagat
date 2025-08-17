import discord
from discord.ext import commands
import json
import os

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="/", intents=intents)

# File paths
PROFILES_FILE = "profiles.json"
BANNED_FILE = "banned.json"

# Load or initialize data
if os.path.exists(PROFILES_FILE):
    with open(PROFILES_FILE, "r") as f:
        user_profiles = json.load(f)
else:
    user_profiles = {}

if os.path.exists(BANNED_FILE):
    with open(BANNED_FILE, "r") as f:
        banned_users = set(json.load(f))
else:
    banned_users = set()

PENDING_ROLE_NAME = "Pending"
VERIFIED_ROLE_NAME = "Verified"
WELCOME_CHANNEL_NAME = "welcome"  # Replace with your welcome channel

def save_profiles():
    with open(PROFILES_FILE, "w") as f:
        json.dump(user_profiles, f, indent=4)

def save_banned():
    with open(BANNED_FILE, "w") as f:
        json.dump(list(banned_users), f, indent=4)

class ProfileModal(discord.ui.Modal, title="Complete Your Profile"):
    gender = discord.ui.TextInput(label="Gender", placeholder="Male / Female / Other", required=True)
    location = discord.ui.TextInput(label="Location", placeholder="Your city", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        location_value = self.location.value.strip().lower()

        # Kick non-London users
        if location_value != "london":
            banned_users.add(interaction.user.id)
            save_banned()
            try:
                await interaction.user.send(
                    "❌ You are not from London, so you have been removed from the server."
                )
            except discord.Forbidden:
                pass
            await interaction.user.kick(reason="Not from London")
            await interaction.response.send_message(
                "❌ You are not from London. You have been removed from the server.",
                ephemeral=True
            )
            return

        # Save profile
        user_profiles[str(interaction.user.id)] = {
            "gender": self.gender.value,
            "location": self.location.value.strip()
        }
        save_profiles()

        guild = interaction.guild

        # Remove Pending role
        pending_role = discord.utils.get(guild.roles, name=PENDING_ROLE_NAME)
        if pending_role:
            try:
                await interaction.user.remove_roles(pending_role)
            except discord.Forbidden:
                pass

        # Get or create Verified role
        role = discord.utils.get(guild.roles, name=VERIFIED_ROLE_NAME)
        if not role:
            try:
                role = await guild.create_role(name=VERIFIED_ROLE_NAME, color=discord.Color.green())
            except discord.Forbidden:
                await interaction.response.send_message(
                    "⚠️ I don't have permission to create roles. Please give me role management permission.",
                    ephemeral=True
                )
                return

        # Assign Verified role
        try:
            await interaction.user.add_roles(role)
            role_msg = f"Role '{VERIFIED_ROLE_NAME}' assigned ✅"
        except discord.Forbidden:
            role_msg = "⚠️ Missing permissions to assign role."

        await interaction.response.send_message(
            f"✅ Profile saved: Gender = {self.gender.value}, Location = {self.location.value}\n{role_msg}",
            ephemeral=True
        )

@bot.event
async def on_member_join(member):
    # Kick if previously banned
    if member.id in banned_users:
        try:
            await member.send(
                "❌ You are not allowed to join this server because you were previously removed for not being from London."
            )
        except discord.Forbidden:
            pass
        await member.kick(reason="Previously banned for not being from London")
        return

    guild = member.guild

    # Create Pending role if it doesn't exist
    pending_role = discord.utils.get(guild.roles, name=PENDING_ROLE_NAME)
    if not pending_role:
        try:
            pending_role = await guild.create_role(name=PENDING_ROLE_NAME)
            for channel in guild.text_channels:
                await channel.set_permissions(pending_role, send_messages=False)
        except discord.Forbidden:
            print("⚠️ Missing permissions to create Pending role or edit channel permissions.")

    # Assign Pending role
    try:
        await member.add_roles(pending_role)
    except discord.Forbidden:
        pass

    # Send modal in server channel
    welcome_channel = discord.utils.get(guild.text_channels, name=WELCOME_CHANNEL_NAME)
    if welcome_channel:
        await welcome_channel.send(
            content=f"🎉 Welcome {member.mention}! Please complete your profile below to access the server.",
            view=discord.ui.View().add_item(
                discord.ui.Button(
                    label="Fill Profile",
                    style=discord.ButtonStyle.primary,
                    custom_id=f"profile_{member.id}"
                )
            )
        )

class ProfileButtonHandler(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Fill Profile", style=discord.ButtonStyle.primary, custom_id="fill_profile")
    async def fill_profile(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.send_modal(ProfileModal())

@bot.event
async def on_ready():
    bot.add_view(ProfileButtonHandler())  # Keep button alive after restart
    await bot.tree.sync()
    print(f"✅ Logged in as {bot.user}")

bot.run("MTQwNjM1NzA5OTI4MTM4NzczMg.Gj4JWE.9UK61zv2aJOkIaSVk564qDRhPJMOzQ_oE7QAow")
