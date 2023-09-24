import asyncio
import base64
import json
import sys
import websockets
import subprocess

import webrtcvad
import wave
import io
import tempfile
import ffmpeg

class colors:
    FINAL = '\033[1m\033[92m'
    INTRM = '\033[91m'

vad = webrtcvad.Vad(1)  # 1 can be replaced with 0, 2 or 3 for different aggressiveness levels
sample_rate = 16000
frame_duration = 20
vad_chunk_size = int(sample_rate * frame_duration / 1000) * 2

async def run():
    extra_headers = {
        'Authorization': ''
    }

    async with websockets.connect(f'wss://api.assemblyai.com/v2/realtime/ws?sample_rate={sample_rate}', extra_headers=extra_headers) as ws:
        async def sender(ws):
            chunk_size = 4096
            pause_time = 0.1

            try:  
                for chunk in iter(lambda: sys.stdin.buffer.read(chunk_size), b''):
                    # OPTION 1: transcode chunk to pcm encoded 16 bit signed mono channel audio
                    # input rtmp stream to pcm encoded 16 bit signed mono channel audio
                    data, stderr = ffmpeg.input('pipe:0').output('pipe:1', format='s16le', acodec='pcm_s16le', ac=1, ar='16000').run_async(pipe_stdin=True, pipe_stdout=True, pipe_stderr=True, quiet=True, overwrite_output=True).communicate(input=chunk)
                    # encode as base64             
                    data = base64.b64encode(data).decode('utf-8')
                    print(stderr)
                    if (len(data) > 0):
                        continue

                    # OPTION 2: convert to temp file and transcode
                    # with tempfile.NamedTemporaryFile(delete=False, suffix='.input') as tmp_input_file:
                    #     tmp_input_file.write(chunk)
                    #     tmp_input_path = tmp_input_file.name

                    # # Name of the temporary output file for transcoded data.
                    # tmp_output_path = tmp_input_path.replace('.input', '.output')

                    # # 2. Transcode the temporary input file to a temporary output file using ffmpeg.
                    # ffmpeg_command = [
                    #     'ffmpeg',
                    #     '-i', tmp_input_path,
                    #     # '-acodec', 'pcm_s16le',
                    #     '-ac', '1',
                    #     '-ar', '16000',
                    #     '-f', 's16le',
                    #     tmp_output_path
                    # ]

                    # subprocess.run(ffmpeg_command, stderr=subprocess.PIPE)

                    # # 3. Read the temporary output file into bytes.
                    # with open(tmp_output_path, 'rb') as tmp_output_file:
                    #     transcoded_data = tmp_output_file.read()

                    # # 4. Encode the bytes as base64.
                    # data = base64.b64encode(transcoded_data).decode('utf-8')
                    



                    # TODO: use a VAD to detect speech start and end
                    # chunk_stream = io.BytesIO(chunk)

                    # is_speech = False
                    # start = 0
                    # end = 0
                    # counter = 0

                    # # Iterate over the micro_chunks inside the chunk
                    # for micro_chunk in iter(lambda: chunk_stream.read(vad_chunk_size), b''):
                        
                    #     # Check if the micro_chunk contains speech
                    #     is_current_chunk_speech = vad.is_speech(micro_chunk, sample_rate)
                        
                    #     if is_current_chunk_speech and not is_speech:
                    #         # Speech started
                    #         print("Speech started")
                    #         is_speech = True
                    #         start = counter
                    #     elif not is_current_chunk_speech and is_speech:
                    #         # Speech ended
                    #         print("Speech ended")
                    #         is_speech = False
                    #         end = counter
                        
                    #     counter += vad_chunk_size

                    # # Handle edge case where speech is ongoing until the end of the chunk
                    # if is_speech:
                    #     end = counter

                    # print(f"Start Speech: {start}, End Speech: {end}")


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
                    # print(response)
                    
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