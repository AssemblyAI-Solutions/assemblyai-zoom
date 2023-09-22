import asyncio
import base64
import json
import sys
import websockets
import subprocess

class colors:
    FINAL = '\033[1m\033[92m'
    INTRM = '\033[91m'

async def run():
    extra_headers = {
        'Authorization': 'YOUR_ASSEMBLY_KEY'
    }

    async with websockets.connect('wss://api.assemblyai.com/v2/realtime/ws?sample_rate=16000', extra_headers=extra_headers) as ws:
        async def sender(ws):
            chunk_size = 4096
            pause_time = 0.1

            # transcode to pcm encoded 16 bit signed mono channel audio only
            ffmpeg_command = [
                'ffmpeg',
                '-i', '-',
                '-acodec', 'pcm_s16le',
                '-ac', '1',
                '-ar', '16000',
                '-f', 's16le',
                '-'
            ]

            ffmpeg_process = subprocess.Popen(
                ffmpeg_command, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE
            )

            try:  
                for chunk in iter(lambda: sys.stdin.buffer.read(chunk_size), b''):
                    # TODO: transcode chunk
                    # data = ffmpeg_process.stdout.read(chunk_size)

                    data = base64.b64encode(chunk).decode('utf-8')
                    await ws.send(json.dumps({
                        "audio_data": data,
                    }))
                    await asyncio.sleep(pause_time)
                await ws.send(json.dumps({
                    "audio_data": "",
                }))
            except Exception as e:
                print(e)
                print('error streaming audio')

        async def receiver(ws):
            async for msg in ws:
                try:
                    response = json.loads(msg)
                    print(response)
                    
                    # Handle session start message
                    if response.get("message_type") == "SessionBegins":
                        print(f"Session Started with ID: {response['session_id']}")
                        print(f"Session Expires At: {response['expires_at']}")
                    
                    # Handle partial transcripts
                    elif response.get("message_type") == "PartialTranscript":
                        start = "{:.2f}".format(response['audio_start'] / 1000)  # Convert ms to seconds
                        end = "{:.2f}".format(response['audio_end'] / 1000)      # Convert ms to seconds
                        print(colors.INTRM + f'[partial] - [{start} - {end}] {response["text"]} {response["words"]}')
                    
                    # Handle final transcripts
                    elif response.get("message_type") == "FinalTranscript":
                        start = "{:.2f}".format(response['audio_start'] / 1000)  # Convert ms to seconds
                        end = "{:.2f}".format(response['audio_end'] / 1000)      # Convert ms to seconds
                        print(colors.FINAL + f'[final] - [{start} - {end}] {response["text"]}')
                        
                        # You can also print punctuated status or other information if needed
                    
                    # Handle unexpected messages
                    else:
                        print(f"Received unexpected message: {response}")

                except Exception as e:
                    print(f'error interpreting ws message: {e}')

        await asyncio.wait([
            asyncio.ensure_future(sender(ws)),
            asyncio.ensure_future(receiver(ws))
        ])

def main():
    asyncio.get_event_loop().run_until_complete(run())

if __name__ == '__main__':
    sys.exit(main() or 0)