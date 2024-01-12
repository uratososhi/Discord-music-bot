import discord
from discord.ext import commands
from discord import FFmpegPCMAudio
from pytube import Playlist, YouTube
from youtubesearchpython import VideosSearch
import asyncio
from pytube.exceptions import RegexMatchError
import os

# bot_version = v3

intents = discord.Intents.all()
intents.members = True

client = commands.Bot(command_prefix='.', intents=intents)

ffmpeg_options = {'options': '-vn'}

songs_queue = []


async def delete_audio_file(file_path, delay):
    await asyncio.sleep(delay)
    try:
        os.remove(file_path)
        print(f"Arquivo {file_path} removido após {delay} segundos.")
    except Exception as e:
        print(f"Erro ao remover o arquivo: {e}")


async def add_playlist_to_queue(ctx, playlist_url):
    try:
        playlist = Playlist(playlist_url)
        for video_url in playlist.video_urls:
            songs_queue.append(video_url)
        await play_next(ctx)  # Iniciar a reprodução da fila
        return True
    except Exception as e:
        print(f'Erro ao adicionar a playlist à fila: {e}')
        return False


@client.command(help='Toca uma playlist do YouTube.')
async def playlist(ctx, *, playlist_url):
    voice_channel = ctx.author.voice.channel
    if voice_channel:
        success = await add_playlist_to_queue(ctx, playlist_url)  # Passar o contexto para a função
        if success:
            await ctx.send('Playlist adicionada à fila.')
        else:
            await ctx.send('Erro ao adicionar a playlist à fila.')
    else:
        await ctx.send('Você precisa estar em um canal de voz para reproduzir uma playlist.')


async def search_and_play(ctx, query):
    voice_channel = ctx.author.voice.channel
    if voice_channel:
        try:
            video = None
            if query and query.startswith("http"):
                video = YouTube(query)
            else:
                video_search = VideosSearch(query, limit=1)
                result = video_search.result()
                if result and 'link' in result['result'][0]:
                    video = YouTube(result['result'][0]['link'])

            if video:
                audio_stream = video.streams.filter(only_audio=True).first()
                audio_path = f"audio_{video.video_id}.mp3"
                audio_stream.download(filename=audio_path)

                voice_client = ctx.voice_client
                if voice_client and voice_client.is_connected():
                    if voice_client.is_playing() or voice_client.is_paused():
                        songs_queue.append(audio_path)
                        await ctx.send(f'{video.title} foi adicionado à fila.')
                    else:
                        voice_client.play(discord.FFmpegPCMAudio(audio_path),
                                          after=lambda e: asyncio.run_coroutine_threadsafe(on_audio_finished(ctx),
                                                                                           client.loop).result())
                        await ctx.send(f'Now playing: {video.title}')

                        if songs_queue:
                            await play_next(ctx)

                    await delete_audio_file(audio_path, 1800)
                else:
                    await voice_channel.connect()
                    await search_and_play(ctx, query)
            else:
                await ctx.send('Nenhum resultado encontrado para a consulta de pesquisa ou URL inválida!')
        except Exception as e:
            await ctx.send(f'Erro: {e}')
    else:
        await ctx.send('Você precisa estar em um canal de voz para reproduzir música!')


async def play_next(ctx):
    voice_client = ctx.voice_client
    if voice_client and not voice_client.is_playing() and songs_queue:
        video_url = songs_queue.pop(0)
        try:
            video = YouTube(video_url)
            audio_stream = video.streams.filter(only_audio=True).first()
            audio_path = f"audio_{video.video_id}.mp3"
            audio_stream.download(filename=audio_path)

            voice_client.play(discord.FFmpegPCMAudio(audio_path),
                              after=lambda e: asyncio.run_coroutine_threadsafe(on_audio_finished(ctx),
                                                                               client.loop).result())

            await ctx.send(f'Now playing: {video.title}')
        except Exception as e:
            await ctx.send(f'Erro ao tocar a música: {e}')
    elif voice_client and not songs_queue:
        await voice_client.disconnect()
    else:
        await search_and_play(ctx, songs_queue[0] if songs_queue else None)


async def on_audio_finished(ctx):
    await play_next(ctx)


@client.command(aliases=['p'], help='Coloca uma música para tocar ou a coloca na fila.')
async def play(ctx, *, query):
    await search_and_play(ctx, query)


@client.command(aliases=['s'], help='Pula a música atual')
async def skip(ctx):
    voice_client = ctx.voice_client
    if not voice_client or not voice_client.is_playing():
        return await ctx.send("Não estou tocando música agora.")

    voice_client.stop()
    await ctx.send("Música pulada.")


@client.command(aliases=['ps'], help='Pausa a música atual.')
async def pause(ctx):
    voice_client = ctx.voice_client
    if not voice_client or not voice_client.is_playing():
        return await ctx.send("Não estou tocando música")


@client.event
async def on_ready():
    print('Bot online')
    print('---------------')


@client.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send(f"Comando '{ctx.message.content.split()[0]}' não reconhecido.")

client.run('YOUR-TOKEN')
