import os
import discord
from discord.ext import commands
import yt_dlp as youtube_dl
import asyncio

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Ensure the 'temp' directory exists
if not os.path.exists('temp'):
    os.makedirs('temp')

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': 'temp/%(extractor)s-%(id)s-%(title)s.%(ext)s',  # Download to temp directory
    'restrictfilenames': True,
    'noplaylist': True,  # Don't download playlists, handle them separately
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'  # Bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')
        self.filename = ytdl.prepare_filename(data)

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # If it's a playlist, return a list of YTDLSource objects
            return [cls(discord.FFmpegPCMAudio(ytdl.prepare_filename(entry), **ffmpeg_options), data=entry) for entry in data['entries']]
        else:
            filename = ytdl.prepare_filename(data)
            return [cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)]

queue = asyncio.Queue()
message_store = []  # Store messages to be deleted

class MediaControl(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=180)
        self.ctx = ctx

    @discord.ui.button(label='Pause', style=discord.ButtonStyle.primary, emoji="⏸️")
    async def pause(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.ctx.voice_client and self.ctx.voice_client.is_playing():
            self.ctx.voice_client.pause()
            await interaction.response.send_message("Paused the current song.", ephemeral=True, delete_after=5)
        else:
            await interaction.response.send_message("No song is playing.", ephemeral=True, delete_after=5)

    @discord.ui.button(label='Resume', style=discord.ButtonStyle.primary, emoji="⏯️")
    async def resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.ctx.voice_client and self.ctx.voice_client.is_paused():
            self.ctx.voice_client.resume()
            await interaction.response.send_message("Resumed the current song.", ephemeral=True, delete_after=5)
        else:
            await interaction.response.send_message("A song is already playing!", ephemeral=True, delete_after=5)

    @discord.ui.button(label='Skip', style=discord.ButtonStyle.primary, emoji="⏭️")
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.ctx.voice_client and self.ctx.voice_client.is_playing():
            self.ctx.voice_client.stop()
            await interaction.response.send_message("Skipped the current song.", ephemeral=True, delete_after=5)
        else:
            await interaction.response.send_message("Are you sure what are you doing?", ephemeral=True, delete_after=5)

    @discord.ui.button(label='Volume -', style=discord.ButtonStyle.primary, emoji="🔉")
    async def volume_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.ctx.voice_client and self.ctx.voice_client.source:
            self.ctx.voice_client.source.volume = max(self.ctx.voice_client.source.volume - 0.1, 0.0)
            await interaction.response.send_message(f"Volume: {int(self.ctx.voice_client.source.volume * 100)}%", ephemeral=True, delete_after=5)

    @discord.ui.button(label='Volume +', style=discord.ButtonStyle.primary, emoji="🔊")
    async def volume_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.ctx.voice_client and self.ctx.voice_client.source:
            self.ctx.voice_client.source.volume = min(self.ctx.voice_client.source.volume + 0.1, 1.0)
            await interaction.response.send_message(f"Volume: {int(self.ctx.voice_client.source.volume * 100)}%", ephemeral=True, delete_after=5)

@bot.command(name='join')
@commands.has_role('ezAdmin')
async def join(ctx):
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        await channel.connect()
    else:
        message = await ctx.send("You are not connected to a voice channel!", delete_after=5)
        message_store.append(message)

async def play_next(ctx):
    if not queue.empty():
        player = await queue.get()
        ctx.voice_client.play(player, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))
        view = MediaControl(ctx)  # Create a new MediaControl view
        message = await ctx.send(f'Now playing: {player.title}', view=view)  # Send the view with the message
        message_store.append(message)
    else:
        await ctx.voice_client.disconnect()
        # Delete downloaded files
        for file in os.listdir('temp'):
            os.remove(os.path.join('temp', file))
        # Delete stored messages
        while message_store:
            message = message_store.pop(0)
            try:
                await message.delete()
            except discord.NotFound:
                continue

@bot.command(name='play')
@commands.has_role('ezAdmin')
async def play(ctx, url=None):
    if url is None:
        message = await ctx.send("Please use !play <youtube link>", delete_after=5)
        message_store.append(message)
        return

    if ctx.voice_client is None:
        if ctx.author.voice:
            channel = ctx.author.voice.channel
            await channel.connect()
        else:
            message = await ctx.send("You are not connected to a voice channel!", delete_after=5)
            message_store.append(message)
            return

    async with ctx.typing():
        try:
            data = await bot.loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
            if 'entries' in data:
                for entry in data['entries']:
                    await queue.put(entry['webpage_url'])
                message = await ctx.send(f'Queued {len(data["entries"])} songs from the playlist.')
                message_store.append(message)
            else:
                await queue.put(url)
                message = await ctx.send(f'Queued: {data["title"]}')
                message_store.append(message)

            if not ctx.voice_client.is_playing():
                await play_next(ctx)
        except Exception as e:
            message = await ctx.send(f"An error occurred while processing the URL: {e}", delete_after=10)
            message_store.append(message)

        # Store the user's command message
        message_store.append(ctx.message)

async def download_and_play(ctx, url):
    async with ctx.typing():
        try:
            player = await YTDLSource.from_url(url, loop=bot.loop, stream=False)
            return player[0]  # Only return the first player (song)
        except Exception as e:
            message = await ctx.send(f"An error occurred while downloading the song: {e}", delete_after=10)
            message_store.append(message)
            return None

async def play_next(ctx):
    if not queue.empty():
        url = await queue.get()
        player = await download_and_play(ctx, url)
        if player:
            ctx.voice_client.play(player, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))
            view = MediaControl(ctx)  # Create a new MediaControl view
            message = await ctx.send(f'Now playing: {player.title}', view=view)  # Send the view with the message
            message_store.append(message)
    else:
        await ctx.voice_client.disconnect()
        # Delete downloaded files
        for file in os.listdir('temp'):
            os.remove(os.path.join('temp', file))
        # Delete stored messages
        while message_store:
            message = message_store.pop(0)
            try:
                await message.delete()
            except discord.NotFound:
                continue

@bot.command(name='skip')
@commands.has_role('ezAdmin')
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        message = await ctx.send("Skipped the current song.", delete_after=5)
        message_store.append(message)
    else:
        message = await ctx.send("No song is currently playing.", delete_after=5)
        message_store.append(message)

@bot.command(name='pause')
@commands.has_role('ezAdmin')
async def pause(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        message = await ctx.send("Paused the current song.", delete_after=5)
        message_store.append(message)
    else:
        message = await ctx.send("No song is currently playing.", delete_after=5)
        message_store.append(message)

@bot.command(name='resume')
@commands.has_role('ezAdmin')
async def resume(ctx):
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        message = await ctx.send("Resumed the current song.", delete_after=5)
        message_store.append(message)
    else:
        message = await ctx.send("No song is currently paused.", delete_after=5)
        message_store.append(message)

@bot.command(name='stop')
@commands.has_role('ezAdmin')
async def stop(ctx):
    if ctx.voice_client:
        ctx.voice_client.stop()
        await ctx.voice_client.disconnect()
        queue._queue.clear()
        # Delete downloaded files
        for file in os.listdir('temp'):
            os.remove(os.path.join('temp', file))
        message = await ctx.send("Stopped and disconnected from the voice channel.", delete_after=5)
        message_store.append(message)

@bot.command(name='leave')
@commands.has_role('ezAdmin')
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        message = await ctx.send("Disconnected from the voice channel.", delete_after=5)
        message_store.append(message)
    else:
        message = await ctx.send("I am not connected to a voice channel.", delete_after=5)
        message_store.append(message)

@bot.command(name='queue')
@commands.has_role('ezAdmin')
async def show_queue(ctx):
    if queue.empty():
        message = await ctx.send("The queue is currently empty.", delete_after=5)
        message_store.append(message)
    else:
        queue_list = []
        async for url in queue._queue:
            info = await bot.loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
            queue_list.append(info.get('title', 'Unknown title'))
        message = await ctx.send(f"Current queue:\n" + "\n".join(queue_list))
        message_store.append(message)

@bot.command(name='clear')
@commands.has_role('ezAdmin')
async def clear(ctx):
    queue._queue.clear()
    message = await ctx.send("Cleared the queue.", delete_after=5)
    message_store.append(message)

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Streaming(name='නෝටි දර්ශන', url='https://www.youtube.com/watch?v=dQw4w9WgXcQ'))
    print('Bot is ready.')

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRole):
        await ctx.send("You do not have the required role to use this command.", delete_after=5)
    else:
        await ctx.send(f"An error occurred: {error}", delete_after=10)
        
bot.run(os.environ['BOT_TOKEN'])