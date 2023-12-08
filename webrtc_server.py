#!/usr/bin/env python3

# Resources
#   https://developer.mozilla.org/en-US/docs/Web/API/WebRTC_API/Signaling_and_video_calling
#   https://developer.mozilla.org/en-US/docs/Web/API/RTCPeerConnection/createAnswer
#   https://codelabs.developers.google.com/codelabs/webrtc-web/#0
#   https://github.com/googlecodelabs/webrtc-web/tree/master (Apache-2.0 License)
#   https://github.com/peers/peerjs
#   about:webrtc
# https://developer.mozilla.org/en-US/docs/Web/API/MediaStreamTrack
#   stream consists of (potentially) multiple tracks: audio, video, ...
# https://developer.mozilla.org/en-US/docs/Web/API/RTCPeerConnection/addTrack
#   adds a new media track to the set of tracks which will be transmitted to the other peer.
# https://developer.mozilla.org/en-US/docs/Web/API/RTCPeerConnection/addStream
#   obsolete!

from http.server import HTTPServer, HTTPStatus, BaseHTTPRequestHandler
import json
import sys


#############
# TEMPLATES #
#############
BASE_TEMPLATE = '''
<!DOCTYPE html>

<html>
<head>
  <title>Test WEBRTC</title>
</head>

<body>
  <h1>Test WEBRTC</h1>
  <div id="content">
    <div>
      <p>Local Video</p>
      <video id="localVideo" autoplay playsinline controls />
    </div>
    <div>
      <p>Remote Video</p>
      <video id="remoteVideo" autoplay playsinline controls />
    </div>

    %s
  </div>

<script type="text/javascript">
'use strict';

const rtc_peer_configuration = {iceServers: [{urls: 'stun:stun.l.google.com:19302'}]}; //change this later
// const rtc_peer_configuration = {iceServers: []};

// Define helper functions.

// Logs an action (text) and the time when it happened on the console.
function trace(text) {
  text = text.trim();
  const now = (window.performance.now() / 1000).toFixed(3);

  console.log(now, text);
}

// In this codelab, you will be streaming video only: "video: true".
// Audio will not be streamed because it is set to "audio: false" by default.
const mediaStreamConstraints = {
  video: true,
};

// Set up to exchange only video.
const offerOptions = {
  offerToReceiveVideo: 1,
};

// Define initial start time of the call (defined as connection between peers).
let startTime = null;

// Define peer connections, streams and video elements.
const localVideo = document.getElementById('localVideo');
const remoteVideo = document.getElementById('remoteVideo');

let localStream;
let remoteStream;

let localPeerConnection;

// Define MediaStreams callbacks.

// Sets the MediaStream as the video element src.
function gotLocalMediaStream(mediaStream) {
  localVideo.srcObject = mediaStream;
  localStream = mediaStream;
  // trace('Received local stream.');
  connectButton.disabled = false;
}

// Handles error by logging a message to the console.
function handleLocalMediaStreamError(error) {
  trace(`navigator.mediaDevices.getUserMedia error: ${error.toString()}.`);
}

// Handles remote MediaStream success by adding it as the remoteVideo src.
function gotRemoteTrack(event) {
  if (event.streams && event.streams[0]) {
    trace('got event.streams[0]');
    const mediaStream = event.streams[0];
    remoteStream = mediaStream;
  } else {
    trace('creating remoteStream');
    if (!remoteStream) {
      remoteStream = new MediaStream();
    }
    remoteStream.addTrack(event.track);
  }
  remoteVideo.srcObject = remoteStream;
  trace('Remote peer connection received remote stream: ' + remoteStream);
}

// Add behavior for video streams.

// Logs a message with the id and size of a video element.
function logVideoLoaded(event) {
  const video = event.target;
  trace(`${video.id} videoWidth: ${video.videoWidth}px, ` +
        `videoHeight: ${video.videoHeight}px.`);
}

// Logs a message with the id and size of a video element.
// This event is fired when video begins streaming.
function logResizedVideo(event) {
  logVideoLoaded(event);

  if (startTime) {
    const elapsedTime = window.performance.now() - startTime;
    startTime = null;
    trace(`Setup time: ${elapsedTime.toFixed(3)}ms.`);
  }
}

localVideo.addEventListener('loadedmetadata', logVideoLoaded);
remoteVideo.addEventListener('loadedmetadata', logVideoLoaded);
remoteVideo.addEventListener('onresize', logResizedVideo);

// Define RTC peer connection behavior.

// Logs changes to the connection state.
function handleConnectionChange(event) {
  const peerConnection = event.target;
  console.log('ICE state change event: ', event);
  trace("ICE state: " + peerConnection.iceConnectionState);
}

// Logs error when setting session description fails.
function setSessionDescriptionError(error) {
  trace(`Failed to create session description: ${error.toString()}.`);
}

// Handles start button action: creates local MediaStream.
function startAction() {
  startButton.disabled = true;
  navigator.mediaDevices.getUserMedia(mediaStreamConstraints)
    .then(gotLocalMediaStream).catch(handleLocalMediaStreamError);
  // trace('Requesting local stream.');
}

// Handles hangup action: ends up call, closes connections and resets peers.
function hangupAction() {
  localPeerConnection.close();
  localPeerConnection = null;
  hangupButton.disabled = true;
  connectButton.disabled = false;
  trace('Ending call.');
}

%s

</script>

</body>
</html>
'''

CLIENT_1_HTML = '''
    <div id="buttons">
      <button id="startButton">Start Local Stream</button>
      <button id="connectButton">Start Call</button>
      <button id="getRemoteButton">Get Remote Stream</button>
      <button id="hangupButton">Hang Up</button>
    </div>
'''

CLIENT_2_HTML = '''
    <div id="buttons">
      <button id="startButton">Start Local Stream</button>
      <button id="connectButton">Connect to Call</button>
      <button id="hangupButton">Hang Up</button>
    </div>
'''

CLIENT_1_JS = '''
// Define action buttons.
const startButton = document.getElementById('startButton');
const connectButton = document.getElementById('connectButton');
const getRemoteButton = document.getElementById('getRemoteButton');
const hangupButton = document.getElementById('hangupButton');

// Set up initial action buttons status: disable call and hangup.
connectButton.disabled = true;
hangupButton.disabled = true;

// Define Client ID (different for different page loads)
let clientId = 1;

// ** store the iceCandidate here, and then add it on a button event!
let iceCandidate;

// Connects with new peer candidate.
function handleConnection(event) {
  console.log("handleConnection start");
  // const peerConnection = event.target;
  iceCandidate = event.candidate;

  // if (iceCandidate) {
  //   console.log("  ice candidate");
  //   const newIceCandidate = new RTCIceCandidate(iceCandidate);
  //   localPeerConnection.addIceCandidate(newIceCandidate)
  //     .then(() => {
  //       trace("addIceCandidate success");
  //     }).catch((error) => {
  //       trace("failed to add ICE Candidate:" + error.toString());
  //     });

  //   trace("ICE candidate:" + event.candidate.candidate);
  // }
  console.log("handleConnection end");
}
// Logs offer creation and sets local peer connection session descriptions;
// posts offer data to server
function createdOffer(description) {
  // trace('localPeerConnection setLocalDescription start.');
  localPeerConnection.setLocalDescription(description)
    .then(() => {}).catch(setSessionDescriptionError);

  const xhr = new XMLHttpRequest();
  xhr.open("POST", "/meet", true);
  // Send the proper header information along with the request
  xhr.setRequestHeader("Content-Type", "application/json; charset=utf-8");
  xhr.onreadystatechange = () => {
    // Call a function when the state changes.
    if (xhr.readyState === XMLHttpRequest.DONE && xhr.status === 200) {
      // Request finished. Do processing here.
      console.log("posted offer");
    }
  };
  xhr.send(JSON.stringify({"id": clientId, "offer": description}));
}

// Handles call button action: creates peer connection.
function connectAction() {
  connectButton.disabled = true;
  hangupButton.disabled = false;

  trace('Starting call.');
  startTime = window.performance.now();

  // Get local media stream tracks.
  // const videoTracks = localStream.getVideoTracks();
  // const audioTracks = localStream.getAudioTracks();
  // if (videoTracks.length > 0) {
  //   // trace(`Using video device: ${videoTracks[0].label}.`);
  // }
  // if (audioTracks.length > 0) {
  //   // trace(`Using audio device: ${audioTracks[0].label}.`);
  // }

  // Create peer connections and add behavior.
  localPeerConnection = new RTCPeerConnection(rtc_peer_configuration);
  // trace('Created local peer connection object localPeerConnection.');

  localPeerConnection.addEventListener('icecandidate', handleConnection);
  localPeerConnection.addEventListener(
    'iceconnectionstatechange', handleConnectionChange);

  localPeerConnection.addEventListener("track", gotRemoteTrack);

  // Add local stream to connection and create offer to connect.
  // localPeerConnection.addStream(localStream);
  // trace('Added local stream to localPeerConnection.');
  for (const track of localStream.getTracks()) {
    trace('adding localStream track to peer connection');
    localPeerConnection.addTrack(track, localStream);
  }

  // trace('localPeerConnection createOffer start.');
  localPeerConnection.createOffer(offerOptions)
    .then(createdOffer).catch(setSessionDescriptionError);
}

// Handles call button action: creates peer connection.
function getRemoteAction() {
  const xhr = new XMLHttpRequest();
  xhr.open("GET", "/meet/" + clientId, true);
  // Send the proper header information along with the request
  xhr.setRequestHeader("Content-Type", "application/json; charset=utf-8");
  xhr.onreadystatechange = () => {
    // Call a function when the state changes.
    if (xhr.readyState === XMLHttpRequest.DONE && xhr.status === 200) {
      // Request finished. Do processing here.
      console.log("got remote description: " + xhr.responseText);
      trace('start setting remote description for other client');
      localPeerConnection.setRemoteDescription(JSON.parse(xhr.responseText))
        .then(() => {
            trace('finished setting remote description - adding ice candidate...');
            const newIceCandidate = new RTCIceCandidate(iceCandidate);
            localPeerConnection.addIceCandidate(newIceCandidate)
              .then(() => {
                trace("addIceCandidate success");
              }).catch((error) => {
                trace("failed to add ICE Candidate:" + error.toString());
              });
        })
        .catch(setSessionDescriptionError);
    }
  };
  xhr.send();
}

// Add click event handlers for buttons.
startButton.addEventListener('click', startAction);
connectButton.addEventListener('click', connectAction);
getRemoteButton.addEventListener('click', getRemoteAction);
hangupButton.addEventListener('click', hangupAction);
'''

CLIENT_2_JS = '''
// Define action buttons.
const startButton = document.getElementById('startButton');
const connectButton = document.getElementById('connectButton');
const hangupButton = document.getElementById('hangupButton');

// Set up initial action buttons status: disable call and hangup.
connectButton.disabled = true;
hangupButton.disabled = true;

let clientId = 2;

let hostOffer = %s;

// Connects with new peer candidate.
function handleConnection(event) {
  console.log("handleConnection start");
  // const peerConnection = event.target;
  const iceCandidate = event.candidate;

  if (iceCandidate) {
    console.log("  ice candidate");
    const newIceCandidate = new RTCIceCandidate(iceCandidate);
    localPeerConnection.addIceCandidate(newIceCandidate)
      .then(() => {
        trace("addIceCandidate success");
      }).catch((error) => {
        trace("failed to add ICE Candidate:" + error.toString());
      });

    trace("ICE candidate:" + event.candidate.candidate);
  }
  console.log("handleConnection end");
}

function joinCall() {
  // Get local media stream tracks.
  // const videoTracks = localStream.getVideoTracks();
  // const audioTracks = localStream.getAudioTracks();
  // if (videoTracks.length > 0) {
  //   // trace(`Using video device: ${videoTracks[0].label}.`);
  // }
  // if (audioTracks.length > 0) {
  //   // trace(`Using audio device: ${audioTracks[0].label}.`);
  // }

  // Create peer connections and add behavior.
  localPeerConnection = new RTCPeerConnection(rtc_peer_configuration);
  // trace('Created local peer connection object localPeerConnection.');

  localPeerConnection.addEventListener('icecandidate', handleConnection);
  localPeerConnection.addEventListener(
    'iceconnectionstatechange', handleConnectionChange);

  localPeerConnection.addEventListener("track", gotRemoteTrack);

  // Add local stream to connection and create offer to connect.
  // localPeerConnection.addStream(localStream);
  // trace('Added local stream to localPeerConnection.');
  for (const track of localStream.getTracks()) {
    trace('adding localStream track to peer connection');
    localPeerConnection.addTrack(track, localStream);
  }

  localPeerConnection.setRemoteDescription(hostOffer)
    .then(() => {
      trace('set the remote description');
    }).catch(setSessionDescriptionError);
  trace('createAnswer start.');
  localPeerConnection.createAnswer()
    .then(createdAnswer)
    .catch(setSessionDescriptionError);
}

// Logs answer to offer creation and sets peer connection session descriptions.
function createdAnswer(description) {
  // trace('localPeerConnection setLocalDescription start.');
  localPeerConnection.setLocalDescription(description)
    .then(() => {}).catch(setSessionDescriptionError);
  console.log("set local description to answer value");

  const xhr = new XMLHttpRequest();
  xhr.open("POST", "/meet", true);
  // Send the proper header information along with the request
  xhr.setRequestHeader("Content-Type", "application/json; charset=utf-8");
  xhr.onreadystatechange = () => {
    // Call a function when the state changes.
    if (xhr.readyState === XMLHttpRequest.DONE && xhr.status === 200) {
      // Request finished. Do processing here.
      console.log("posted answer to server");
    }
  };
  xhr.send(JSON.stringify({"id": clientId, "offer": description}));
}

// Add click event handlers for buttons.
startButton.addEventListener('click', startAction);
connectButton.addEventListener('click', joinCall);
hangupButton.addEventListener('click', hangupAction);
'''

CLIENT_1 = BASE_TEMPLATE % (CLIENT_1_HTML, CLIENT_1_JS)

offers = {0: {}}


def render_template():
    client_id = 0
    if 1 not in offers:
        offers[1] = {}
        return CLIENT_1
    elif 2 not in offers:
        offers[2] = {}
        client_2_js = CLIENT_2_JS % json.dumps(offers[1]['offer'])
        return BASE_TEMPLATE % (CLIENT_2_HTML, client_2_js)
    return ''


MEETING_PATH = '/meet'


class Handler(BaseHTTPRequestHandler):
    def version_string(self):
        return 'Apache'

    def log_request(self, with_headers=False, not_found=False):
        msg = '"%s"'
        if not_found:
            msg = '"%s" => 404 Not Found'
        self.log_message(msg, self.requestline)
        if with_headers:
            self.log_message('  headers:')
            for header, value in self.headers.items():
                self.log_message('    %s: %s', header, value)

    def not_found(self):
        self.log_request(not_found=True)
        self.send_response_only(HTTPStatus.NOT_FOUND)
        self.end_headers()

    def do_GET(self):
        if not self.path.startswith(MEETING_PATH):
            self.not_found()
            return

        self.log_request()

        content_type = 'text/html'

        if self.path.endswith('/1'):
            if 2 in offers and 'offer' in offers[2]:
                content = json.dumps(offers[2]['offer'])
                content_type = 'application/json'
            else:
                content = 'no offer yet'
                content_type = 'text/plain'
        elif self.path.endswith('/2'):
            if 1 in offers and 'offer' in offers[1]:
                content = json.dumps(offers[1]['offer'])
                content_type = 'application/json'
            else:
                content = 'no offer yet'
                content_type = 'text/plain'
        else:
            content = render_template()

        encoded_content = content.encode('utf8')

        self.send_response_only(HTTPStatus.OK)
        self.send_header('Server', self.version_string())
        self.send_header('Date', self.date_time_string())
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', len(encoded_content))
        self.end_headers()
        self.wfile.write(encoded_content)

    def do_POST(self):
        if not self.path.startswith(MEETING_PATH):
            self.not_found()
            return

        self.log_request(with_headers=False)

        content_length = self.headers.get('Content-Length')
        try:
            size = int(content_length)
        except (TypeError, ValueError):
            size = 0

        body = self.rfile.read(size)
        if body:
            content_type = self.headers.get('Content-Type')
            body = body.decode('utf8')
            if content_type.startswith('application/json'):
                data = json.loads(body)
                offers[data['id']]['offer'] = data['offer']
                print(offers.keys())
            else:
                print(f'{body=}')

        self.send_response_only(HTTPStatus.OK)
        self.send_header('Server', self.version_string())
        self.send_header('Date', self.date_time_string())
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.end_headers()

        self.wfile.write('finished POST handling'.encode('utf8'))


def main(port=8000):
    with HTTPServer(('', port), Handler) as httpd:
        print(f'Serving on port {port}...')
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nKeyboard interrupt received, exiting.")
            sys.exit(0)


if __name__ == '__main__':
    main()
