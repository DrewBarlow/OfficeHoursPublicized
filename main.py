import discord
from discord.ext import commands

client = commands.Bot(command_prefix=commands.when_mentioned_or("!"))
TOKEN = ""  # Token here

@client.event
async def on_ready():
    pres = discord.Activity(name="0 queues.", type=discord.ActivityType.watching)
    await client.change_presence(status=discord.Status.dnd, activity=pres)
    print("Office Hours Ready")


client.load_extension('OHHandling.OHHandling')
client.run(TOKEN)
