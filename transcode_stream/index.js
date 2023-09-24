const ASSEMBLYAI_API_KEY = "7ca19699f6fe471da558028fc9414e06" // TODO: replace with your API key
const RTMP_URL = "rtmp://0.tcp.ngrok.io:11107/live/ASSEMBLY" // TODO: replace with your RTSP URL

const WebSocket = require('ws');
const VAD = require('node-vad'); // other libs include Praat or Essentia
const spawn = require('child_process').spawn;

const vad = new VAD(VAD.Mode.NORMAL, 16000);

const word_boost = [] // TODO: Add custom vocabulary to boost e.g. ['foo', 'bar']
const params = {"sample_rate": 16000, "word_boost": JSON.stringify(word_boost)}

const axios = require('axios');

async function getAssemblyAIToken() {
  const url = 'https://api.assemblyai.com/v2/realtime/token';
  const headers = {
    'authorization': ASSEMBLYAI_API_KEY,
    'Content-Type': 'application/json'
  };
  const data = {
    expires_in: 60
  };

  try {
    const response = await axios.post(url, data, { headers });
    return response.data;
  } catch (error) {
    throw error;
  }
}

// Optional: Get a temporary token from AssemblyAI
getAssemblyAIToken()
  .then(tokenData => {
    console.log('Token data:', tokenData);
    params['token'] = tokenData['token'];
  })
  .catch(error => {
    console.error('Error:', error.message);
  });

const url = "wss://api.assemblyai.com/v2/realtime/ws?" + new URLSearchParams(params).toString();

const ws = new WebSocket(url, {
    headers: {
        Authorization: ASSEMBLYAI_API_KEY,
    }
});

const sentQueue = []
let previousVadState = VAD.Event.SILENCE;  // assume starting in silence
let voiceStartTimestamp = null;
let websocketOpenTS = null;

ws.on('open', function open() {
    const ffmpeg = spawn('ffmpeg', ['-i', RTMP_URL, '-acodec', 'pcm_s16le', '-ac', '1', '-ar', '16000', '-f', 's16le', '-']);
    // print ffmpeg command
    let buffer = Buffer.alloc(0);

    ffmpeg.stdout.on('data', (data) => {
        buffer = Buffer.concat([buffer, data]);
        const buffer_size = 4096;
        while (buffer.length >= buffer_size) {
            const chunk = buffer.slice(0, buffer_size);
            buffer = buffer.slice(buffer_size);

            vad.processAudio(chunk, 16000).then(res => {
              switch (res) {
                  case VAD.Event.VOICE:
                      if (previousVadState !== VAD.Event.VOICE) {
                          voiceStartTimestamp = Date.now() - websocketOpenTS;  // this marks the beginning of voice segment
                      }
                      break;
                  case VAD.Event.SILENCE:
                      if (previousVadState === VAD.Event.VOICE && voiceStartTimestamp !== null) {
                          sentQueue.push({
                              start: voiceStartTimestamp,
                              end: Date.now() - websocketOpenTS // the end of the voice segment
                          });
                          voiceStartTimestamp = null; // reset for the next segment
                      }
                      break;
              }
              previousVadState = res;
            }).catch(console.error);

            if (ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({
                    audio_data: chunk.toString('base64')
                }), (error) => {
                    if (error) console.error(error);
                });
            }
        }
    });

    ffmpeg.stderr.on('data', (data) => {
        // console.error(`stderr: ${data}`);
    });

    ffmpeg.on('close', (code) => {
        console.log(`child process exited with code ${code}`);
    });

    ws.on('close', () => {
        ffmpeg.kill();
    });
});

ws.on('message', function incoming(message) {
    const data = JSON.parse(message);
    // console.log(data);
    if (data.message_type === 'PartialTranscript') {
      if (sentQueue.length >= 0) {
        const matchingSegment = sentQueue.shift();

        if (matchingSegment && data.words && data.words.length > 0) {
          
          // const driftStart = data.audio_start - matchingSegment.start;
          // const driftEnd = data.audio_end - matchingSegment.end;

          // Apply offset to transcription timestamps
          // data.words.forEach(word => {
          //     word.start -= driftStart;
          //     word.end -= driftEnd;
          // });

          data.vad_audio_start = matchingSegment.start;
          data.vad_audio_end = matchingSegment.end;
          console.log(data);
        }
      }
      // console.log(data);
    }
    else if (data.message_type === 'SessionBegins'){
      console.log(data);
      websocketOpenTS = Date.now();
  }
});
