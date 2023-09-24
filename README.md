# AssemblyAI + Zoom Live Streaming Integration [INTERNAL USE ONLY]

### Installation

1. Clone this repository
2. `pip install -r requirements.txt` (or `pip3` depending on your Python installation)
3. On line 17 of `stream.py`, replace `YOUR_ASSEMBLY_KEY` with your Assembly API Key

### Create a Zoom Pro Account
Before you can use Zoom’s live streaming, you'll need to create a Zoom Pro account. Then enable the following:

- livestreaming for meetings and webinars
- livestreaming to a custom service

### Install Development Dependencies
In order to run the services required for this integration, you will need to brew install the following:

- npm
- FFmpeg
- ngrok
- rtmpdump

### Steps to run Zoom to AssemblyAI pipeline
1. Start the input server to collect the Zoom stream: `npm i node-media-server -g && node-media-server`
2. Ngrok it: `ngrok tcp 1935`
3. Start your Zoom meeting and set your stream details (click More > Live on Custom Live Streaming Service)
4. Set your Streaming URL to the Ngrok server URL but replace `tcp://` with `rtmp://` and append `/live` to the end of the URL. For example, if your Ngrok URL is `tcp://0.tcp.ngrok.io:12345`, your Streaming URL should be `rtmp://0.tcp.ngrok.io:12345/live`. Then, set your Streaming key to ASSEMBLY and click Go Live
5. <del>Then in your terminal, run `source stream_rtmp.sh {YOUR_STREAMING_URL} ASSEMBLY`</del>
6. <del>The Zoom stream should now be streaming through the input server and into AssemblyAI. The output will be logged in your terminal.</del>
7. cd into ./transcode_stream and update your Assembly API Key and RTMP URL in `index.js` and npm install all the dependencies
8. Run `node index.js` to start reading the stream. The RTMP stream will be transcoded in real-time with FFMPEG and sent to the AssemblyAI Real-Time Websocket for transcription.