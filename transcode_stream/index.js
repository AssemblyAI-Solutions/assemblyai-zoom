const ASSEMBLYAI_API_KEY = "" // TODO: replace with your API key
const RTMP_URL = "rtmp://0.tcp.ngrok.io:11107/live/ASSEMBLY" // TODO: replace with your RTSP URL

const WebSocket = require('ws');
const spawn = require('child_process').spawn;

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
    if (data.message_type === 'PartialTranscript'){
        console.log(data.words);
    }
    else if (data.message_type === 'SessionBegins'){
      console.log(data);
  }
});
