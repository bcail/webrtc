#!/usr/bin/env python3
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
    <div id="client_id"></div>

    %s
  </div>

  <script>
  const config = {
    iceServers: [{ urls: "stun:stun.l.google.com:19302" }],
  };

function log_states(pc) {
  console.log("connection state: ", pc.connectionState);
  console.log("signaling state: ", pc.signalingState);
}

  const pc = new RTCPeerConnection(config);
  log_states(pc);

function start_data_channel() {
  console.log("starting data channel...");
  let dataChannel = pc.createDataChannel("MyApp Channel");
  dataChannel.addEventListener("open", (event) => {
    // beginTransmission(dataChannel);
    console.log("channel open!");
  });
}

  %s

  pc.addEventListener('icecandidate', handle_ice_candidate);
  pc.addEventListener('iceconnectionstatechange', handle_connection_change);
  </script>
</body>
</html>
'''

CLIENT_1_HTML = '''
  <button id="getAnswer">Get Answer</button>
'''

CLIENT_1_JS = '''
  var client_id = 1;
  document.getElementById("client_id").innerText = "Client 1";

  // ** store the iceCandidate here, and then add it on a button event!
  let iceCandidate;

function handle_ice_candidate(event) {
  console.log("handle_ice_candidate: " + event.candidate);
  iceCandidate = event.candidate;
}

function handle_connection_change(event) {
  console.log('ICE state change event: ', event);
}

function createdOffer(description) {
  pc.setLocalDescription(description)
    .then(() => {}).catch( (error) => {
        console.log("set local description error" + error);
      }
    );

  const xhr = new XMLHttpRequest();
  xhr.open("POST", "/meet", true);
  xhr.setRequestHeader("Content-Type", "application/json; charset=utf-8");

  xhr.onreadystatechange = () => {
    if (xhr.readyState === XMLHttpRequest.DONE && xhr.status === 200) {
      console.log("posted offer");
      log_states(pc);
    }
  };

  xhr.send(JSON.stringify({"id": client_id, "offer": description}));
}

function get_answer() {
  const xhr = new XMLHttpRequest();
  xhr.open("GET", "/meet/" + client_id, true);
  xhr.setRequestHeader("Content-Type", "application/json; charset=utf-8");
  xhr.onreadystatechange = () => {
    if (xhr.readyState === XMLHttpRequest.DONE && xhr.status === 200) {
      console.log("got remote description: " + xhr.responseText);
      pc.setRemoteDescription(JSON.parse(xhr.responseText))
        .then(() => {
            console.log('finished setting remote description');
            const newIceCandidate = new RTCIceCandidate(iceCandidate);
            pc.addIceCandidate(newIceCandidate)
              .then(() => {
                console.log("addIceCandidate success");
                log_states(pc);
              }).catch((error) => {
                console.log("failed to add ICE Candidate: " + error.toString());
              });
          })
        .catch( (error) => {
            console.log("error setting remote description: " + error);
          }
        );
    }
  };
  xhr.send();
}

  start_data_channel();
  pc.createOffer()
    .then(createdOffer).catch( (error) => {
        console.log("created offer error: " + error);
      }
    );


  const get_answer_button = document.getElementById('getAnswer');
  get_answer_button.addEventListener('click', get_answer);
'''

CLIENT_2_HTML = '''
'''

CLIENT_2_JS = '''
  var client_id = 2;
  document.getElementById("client_id").innerText = "Client " + client_id;

  let hostOffer = %s;
  let receiveChannel = null;

function handle_ice_candidate(event) {
  console.log("handle_ice_candidate: " + event.candidate);
  const newIceCandidate = new RTCIceCandidate(event.candidate);
  pc.addIceCandidate(newIceCandidate)
    .then(() => {
      console.log("addIceCandidate success");
    }).catch((error) => {
      console.log("failed to add ICE Candidate: " + error.toString());
    });
}

function handle_connection_change(event) {
  console.log('ICE state change event: ', event);
}

function createdAnswer(description) {
  pc.setLocalDescription(description)
    .then(() => {
        console.log("set local description to answer value");
      }
    ).catch( (error) => {
        console.log("set local description error: " + error);
      }
    );

  const xhr = new XMLHttpRequest();
  xhr.open("POST", "/meet", true);
  xhr.setRequestHeader("Content-Type", "application/json; charset=utf-8");
  xhr.onreadystatechange = () => {
    if (xhr.readyState === XMLHttpRequest.DONE && xhr.status === 200) {
      console.log("posted answer to server");
      log_states(pc);
    }
  };
  xhr.send(JSON.stringify({"id": client_id, "offer": description}));
}

function handleReceiveMessage(msg) {
  console.log("received message");
}

function handleReceiveChannelStatusChange(event) {
  console.log("receive channel status change");
}

function receiveChannelCallback(event) {
  console.log("received channel");
  receiveChannel = event.channel;
  receiveChannel.onmessage = handleReceiveMessage;
  receiveChannel.onopen = handleReceiveChannelStatusChange;
  receiveChannel.onclose = handleReceiveChannelStatusChange;
}

  pc.ondatachannel = receiveChannelCallback;

  pc.setRemoteDescription(hostOffer)
    .then(() => {
      console.log('set the remote description');
    }).catch( (error) => {
        console.log("set remote description error: " + error);
      }
    );
  pc.createAnswer()
    .then(createdAnswer)
    .catch( (error) => {
        console.log("created answer error: " + error);
      }
    );
'''


CLIENT_1 = BASE_TEMPLATE % (CLIENT_1_HTML, CLIENT_1_JS)
CLIENT_2 = BASE_TEMPLATE % (CLIENT_2_HTML, CLIENT_2_JS)

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
