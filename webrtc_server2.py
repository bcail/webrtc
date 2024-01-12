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
# https://blog.mozilla.org/webrtc/perfect-negotiation-in-webrtc/
# https://developer.mozilla.org/en-US/docs/Web/API/WebRTC_API/Perfect_negotiation

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

    <script>
      var client_id = 1;
      document.getElementById("client_id").innerText = "Client 1";
    </script>
'''

CLIENT_2_HTML = '''
    <div id="buttons">
      <button id="startButton">Start Local Stream</button>
      <button id="connectButton">Connect to Call</button>
      <button id="hangupButton">Hang Up</button>
    </div>

    <script>
      var client_id = 2;
      document.getElementById("client_id").innerText = "Client 2";
    </script>
'''


CLIENT_1 = BASE_TEMPLATE % CLIENT_1_HTML
CLIENT_2 = BASE_TEMPLATE % CLIENT_2_HTML

offers = {0: {}}


def render_template():
    client_id = 0
    if 1 not in offers:
        offers[1] = {}
        return CLIENT_1
    elif 2 not in offers:
        offers[2] = {}
        return CLIENT_2
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
