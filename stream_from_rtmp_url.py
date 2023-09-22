import asyncio
import websockets
import subprocess
import json
import base64

async def send_audio_data(ws, ffmpeg_process):
    while True:
        data = ffmpeg_process.stdout.read(4096)
        if not data:
            break
        await ws.send(json.dumps({
            "audio_data": base64.b64encode(data).decode('utf-8'),
        }))

    ffmpeg_process.terminate()

async def receive_responses(ws):
    async for message in ws:
        print("Received message from AssemblyAI:", message)

async def stream_to_websocket(rtmp_url, sample_rate):
    websocket_url = f"wss://api.assemblyai.com/v2/realtime/ws?sample_rate={sample_rate}"

    cmd = [
        "ffmpeg", 
        "-loglevel", "error",
        "-i", rtmp_url,
        "-f", "s16le",
        "-acodec", "pcm_s16le",
        "-ac", "1",
        "-vn",
        "-ar", sample_rate,
        "-preset", "ultrafast",
        "-"
    ]

    ffmpeg_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    headers = {
        "authorization": "7ca19699f6fe471da558028fc9414e06"  # Replace with your AssemblyAI API key
    }

    async with websockets.connect(websocket_url, extra_headers=headers) as ws:
        # Using asyncio.gather to send audio and receive messages concurrently
        await asyncio.gather(
            send_audio_data(ws, ffmpeg_process),
            receive_responses(ws)
        )

# Example usage:
rtmp_stream = "rtmp://8.tcp.ngrok.io:15618/live/ASSEMBLY" # replace with your RTMP stream URL
sample_rate = "16000"
asyncio.run(stream_to_websocket(rtmp_stream, sample_rate))