import os
import threading
from uuid import uuid4

import yt_dlp
from flask import Flask, request, jsonify, send_file
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configuração da pasta de downloads
DOWNLOAD_FOLDER = '/opt/awesome-videotube-downloader'

# Cria a pasta de downloads se não existir
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# Estrutura para armazenar o estado das tarefas
tasks = {}
tasks_lock = threading.Lock()


def download_video(video_id, url):
    """
    Função que realiza o download do vídeo e atualiza o estado da tarefa.
    """
    with tasks_lock:
        tasks[video_id]['status'] = 'em andamento'

    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'merge_output_format': 'mp4',
        'outtmpl': os.path.join(DOWNLOAD_FOLDER, f'{video_id}.%(ext)s'),
        'concurrent_fragment_downloads': 16,
        'external_downloader_args': ['-x', '--max-connection-per-server=16'],
        'noprogress': False,
        'no_warnings': False,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            # Renomeia o arquivo para task_id com a extensão correta
            base, ext = os.path.splitext(filename)
            secure_name = secure_filename(f"{video_id}{ext}")
            final_path = os.path.join(DOWNLOAD_FOLDER, secure_name)
            os.rename(filename, final_path)

        with tasks_lock:
            tasks[video_id]['status'] = 'concluído'
            tasks[video_id]['file_path'] = final_path
    except Exception as e:
        with tasks_lock:
            tasks[video_id]['status'] = 'falhou'
            tasks[video_id]['error'] = str(e)


@app.route('/video/request-download', methods=['POST'])
def initiate_download():
    """
    Endpoint para iniciar o download do vídeo.
    Espera um JSON com a chave 'url'.
    Retorna um 'task_id' para acompanhar o status.
    """
    data = request.get_json()
    url = data.get('url')

    if not url:
        return jsonify({'error': 'Nenhuma URL fornecida.'}), 400

    # Gera um ID único para a tarefa
    video_id = str(uuid4())

    # Inicializa o estado da tarefa
    with tasks_lock:
        tasks[video_id] = {
            'status': 'pendente',
            'file_path': None,
            'error': None
        }

    # Inicia o download em uma thread separada
    thread = threading.Thread(target=download_video, args=(video_id, url))
    thread.start()

    return jsonify({
        'video_id': video_id,
        'status': 'pendente',
        'message': 'O download foi iniciado. Verifique o status da tarefa para obter o arquivo.'
    }), 202


@app.route('/video/<video_id>', methods=['GET'])
def check_status(video_id):
    """
    Endpoint para verificar o status da tarefa.
    Retorna o status e, se concluído, o link para download.
    """
    with tasks_lock:
        task = tasks.get(video_id)

    if not task:
        return jsonify({'error': 'ID da tarefa não encontrado.'}), 404

    response = {'status': task['status']}

    if task['status'] == 'concluído':
        response['video_id'] = video_id
    elif task['status'] == 'falhou':
        response['error'] = task.get('error', 'Ocorreu um erro desconhecido.')

    return jsonify(response)


def erase_file_after_download(file_path, video_id):
    try:
        os.remove(file_path)
        with tasks_lock:
            del tasks[video_id]
        app.logger.info(f"Arquivo {file_path} removido com sucesso.")
    except Exception as e:
        app.logger.error(f"Erro ao remover o arquivo {file_path}: {e}")
    return


@app.route('/video/<video_id>/download', methods=['GET'])
def download_file(video_id):
    """
    Endpoint para baixar o arquivo após a conclusão do download.
    Apaga o arquivo após o envio.
    """
    with tasks_lock:
        task = tasks.get(video_id)

    if not task:
        return jsonify({'error': 'ID da tarefa não encontrado.'}), 404

    if task['status'] != 'concluído' or not task.get('file_path'):
        return jsonify({'error': 'Arquivo não disponível para download.'}), 400

    file_path = task['file_path']

    if not os.path.exists(file_path):
        return jsonify({'error': 'Arquivo não encontrado no servidor.'}), 404

    # Define o nome do arquivo para o cliente
    filename = os.path.basename(file_path)

    threading.Timer(1800, erase_file_after_download, args=[file_path, video_id]).start()

    return send_file(file_path, download_name=filename, as_attachment=True)


if __name__ == '__main__':
    # Executa a aplicação Flask
    app.run(host='0.0.0.0', port=5000, debug=True)
