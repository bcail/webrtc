#!/usr/bin/env python3

# Resources
#   https://developer.mozilla.org/en-US/docs/Web/API/WebRTC_API/Signaling_and_video_calling
#   https://developer.mozilla.org/en-US/docs/Web/API/RTCPeerConnection/createAnswer
#   https://codelabs.developers.google.com/codelabs/webrtc-web/#0
#   https://github.com/googlecodelabs/webrtc-web/tree/master (Apache-2.0 License)

from http.server import HTTPServer, HTTPStatus, BaseHTTPRequestHandler
import json
import random
import sys


#############
# TEMPLATES #
#############
BASE_HTML = '''
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
      <video id="localVideo" autoplay playsinline />
    </div>
    <div>
      <p>Remote Video</p>
      <video id="remoteVideo" autoplay playsinline />
    </div>

    <div>
      <button id="startButton">Start Local Stream</button>
      <button id="connectButton">Connect</button>
      <button id="getRemoteButton">Get Remote Stream</button>
      <button id="hangupButton">Hang Up</button>
    </div>
  </div>

<script type="text/javascript">
'use strict';

// Define helper functions.

// Gets the "other" peer connection.
function getOtherPeer(peerConnection) {
  return (peerConnection === localPeerConnection) ?
      remotePeerConnection : localPeerConnection;
}

// Gets the name of a certain peer connection.
function getPeerName(peerConnection) {
  return (peerConnection === localPeerConnection) ?
      'localPeerConnection' : 'remotePeerConnection';
}

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
let remotePeerConnection;

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
  trace(`navigator.getUserMedia error: ${error.toString()}.`);
}

// Handles remote MediaStream success by adding it as the remoteVideo src.
function gotRemoteMediaStream(event) {
  const mediaStream = event.stream;
  remoteVideo.srcObject = mediaStream;
  remoteStream = mediaStream;
  trace('Remote peer connection received remote stream.');
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

// Connects with new peer candidate.
function handleConnection(event) {
  const peerConnection = event.target;
  const iceCandidate = event.candidate;

  if (iceCandidate) {
    const newIceCandidate = new RTCIceCandidate(iceCandidate);
    const otherPeer = getOtherPeer(peerConnection);

    otherPeer.addIceCandidate(newIceCandidate)
      .then(() => {
        handleConnectionSuccess(peerConnection);
      }).catch((error) => {
        handleConnectionFailure(peerConnection, error);
      });

    trace(`${getPeerName(peerConnection)} ICE candidate:\n` +
          `${event.candidate.candidate}.`);
  }
}

// Logs that the connection succeeded.
function handleConnectionSuccess(peerConnection) {
  trace(`${getPeerName(peerConnection)} addIceCandidate success.`);
};

// Logs that the connection failed.
function handleConnectionFailure(peerConnection, error) {
  trace(`${getPeerName(peerConnection)} failed to add ICE Candidate:\n`+
        `${error.toString()}.`);
}

// Logs changes to the connection state.
function handleConnectionChange(event) {
  const peerConnection = event.target;
  console.log('ICE state change event: ', event);
  trace(`${getPeerName(peerConnection)} ICE state: ` +
        `${peerConnection.iceConnectionState}.`);
}

// Logs error when setting session description fails.
function setSessionDescriptionError(error) {
  trace(`Failed to create session description: ${error.toString()}.`);
}

// Logs success when setting session description.
function setDescriptionSuccess(peerConnection, functionName) {
  const peerName = getPeerName(peerConnection);
  trace(`${peerName} ${functionName} complete.`);
}

// Logs success when localDescription is set.
function setLocalDescriptionSuccess(peerConnection) {
  setDescriptionSuccess(peerConnection, 'setLocalDescription');
}

// Logs success when remoteDescription is set.
function setRemoteDescriptionSuccess(peerConnection) {
  setDescriptionSuccess(peerConnection, 'setRemoteDescription');
}

// Define and add behavior to buttons.

// Define action buttons.
const startButton = document.getElementById('startButton');
const connectButton = document.getElementById('connectButton');
const getRemoteButton = document.getElementById('getRemoteButton');
const hangupButton = document.getElementById('hangupButton');

// Set up initial action buttons status: disable call and hangup.
connectButton.disabled = true;
hangupButton.disabled = true;

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
  remotePeerConnection.close();
  localPeerConnection = null;
  remotePeerConnection = null;
  hangupButton.disabled = true;
  connectButton.disabled = false;
  trace('Ending call.');
}

%s

</script>
</body>
</html>
'''

CONNECT_HTML = BASE_HTML % '''
// Define Client ID (different for different page loads)
let clientId = %s;

// Logs offer creation and sets local peer connection session descriptions;
// posts offer data to server
function createdOffer(description) {
  // trace('localPeerConnection setLocalDescription start.');
  localPeerConnection.setLocalDescription(description)
    .then(() => {
      // setLocalDescriptionSuccess(localPeerConnection);
    }).catch(setSessionDescriptionError);

  const xhr = new XMLHttpRequest();
  xhr.open("POST", "/meet", true);
  // Send the proper header information along with the request
  xhr.setRequestHeader("Content-Type", "application/json; charset=utf-8");
  xhr.onreadystatechange = () => {
    // Call a function when the state changes.
    if (xhr.readyState === XMLHttpRequest.DONE && xhr.status === 200) {
      // Request finished. Do processing here.
      console.log("request finished");
    }
  };
  xhr.send(JSON.stringify({"id": clientId, "offer": description}));

}

// Logs answer to offer creation and sets peer connection session descriptions.
function createdAnswer(description) {
  trace(`Answer from remotePeerConnection:\n${description.sdp}.`);

  trace('remotePeerConnection setLocalDescription start.');
  remotePeerConnection.setLocalDescription(description)
    .then(() => {
      setLocalDescriptionSuccess(remotePeerConnection);
    }).catch(setSessionDescriptionError);

  trace('localPeerConnection setRemoteDescription start.');
  localPeerConnection.setRemoteDescription(description)
    .then(() => {
      setRemoteDescriptionSuccess(localPeerConnection);
    }).catch(setSessionDescriptionError);
}

// Handles call button action: creates peer connection.
function connectAction() {
  connectButton.disabled = true;
  hangupButton.disabled = false;

  trace('Starting call.');
  startTime = window.performance.now();

  // Get local media stream tracks.
  const videoTracks = localStream.getVideoTracks();
  const audioTracks = localStream.getAudioTracks();
  if (videoTracks.length > 0) {
    // trace(`Using video device: ${videoTracks[0].label}.`);
  }
  if (audioTracks.length > 0) {
    // trace(`Using audio device: ${audioTracks[0].label}.`);
  }

  const servers = null;  // Allows for RTC server configuration.

  // Create peer connections and add behavior.
  localPeerConnection = new RTCPeerConnection(servers);
  // trace('Created local peer connection object localPeerConnection.');

  localPeerConnection.addEventListener('icecandidate', handleConnection);
  localPeerConnection.addEventListener(
    'iceconnectionstatechange', handleConnectionChange);

  remotePeerConnection = new RTCPeerConnection(servers);
  // trace('Created remote peer connection object remotePeerConnection.');

  remotePeerConnection.addEventListener('icecandidate', handleConnection);
  remotePeerConnection.addEventListener(
    'iceconnectionstatechange', handleConnectionChange);
  remotePeerConnection.addEventListener('addstream', gotRemoteMediaStream);

  // Add local stream to connection and create offer to connect.
  localPeerConnection.addStream(localStream);
  // trace('Added local stream to localPeerConnection.');

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
      console.log("request finished: " + xhr.responseText);
      trace('remotePeerConnection setRemoteDescription start.');
      remotePeerConnection.setRemoteDescription(JSON.parse(xhr.responseText))
        .then(() => {
          setRemoteDescriptionSuccess(remotePeerConnection);
        }).catch(setSessionDescriptionError);
      trace('remotePeerConnection createAnswer start.');
      remotePeerConnection.createAnswer()
        .then(createdAnswer)
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


offers = {0: {}}


def render_template():
    client_id = 0
    for i in range(1, 3):
        if i not in offers:
            offers[i] = {}
            client_id = i
            break
    return CONNECT_HTML % client_id


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
