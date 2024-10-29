import argparse

import yt_dlp


def parse_args():
    parser = argparse.ArgumentParser(description='Download Youtube videos')

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-u', '--url', type=str, help='URL of the Youtube video')
    group.add_argument('-f', '--file', type=str, help='File containing list of Youtube videos')

    parser.add_argument('-o', '--output', type=str, help='Output path to save the video', required=True)

    return parser.parse_args()


def handle_url_download(url: str, output_dir: str):
    pass


def on_progress_callback(d):
    if d['status'] == 'downloading':
        print(f"Baixando: {d['_percent_str']} a {d['_speed_str']}")
        format_id = d.get('format_id')
        print(f"Formato do download: {format_id}")
    elif d['status'] == 'finished':
        print("Download concluído!")
    elif d['status'] == 'error':
        print("Erro no download!")


def download_video_with_dlp(urls: [str], output_dir: str):
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'merge_output_format': 'mp4',
        'outtmpl': f'{output_dir}/%(title)s.%(ext)s',
        'concurrent_fragment_downloads': 16,
        'external_downloader_args': ['-x', '--max-connection-per-server=16'],
        'noprogress': False,
        'no_warnings': False,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download(urls)


def handle_file_download(file: str, output_dir: str):
    urls = []
    with open(file, 'r') as content:
        for line in content:
            if line.strip != '':
                urls.append(line.strip())

    download_video_with_dlp(urls, output_dir)


if __name__ == '__main__':
    args = parse_args()

    if args.url:
        handle_url_download(
            url=args.url,
            output_dir=args.output
        )
    elif args.file:
        handle_file_download(
            file=args.file,
            output_dir=args.output
        )
