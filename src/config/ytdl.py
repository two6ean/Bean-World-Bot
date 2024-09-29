import yt_dlp as youtube_dl

# yt-dlp 포맷 옵션 설정
ytdl_format_options = {
    'format': 'bestaudio[ext=m4a]/bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': False,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'cookiefile': 'cookies.txt',
    'ratelimit': '10M',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '32',
    }, {
        'key': 'FFmpegMetadata',
    }],
    'extractor_args': {
        'youtubetab': {
            'skip': ['authcheck']
        }
    }
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -af atempo=1.05,aresample=44100 -sn -dn -bufsize 64M -timeout 10000000 -loglevel info'
}