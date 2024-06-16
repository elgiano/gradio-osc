from .server import GradioOSCServer
from threading import Thread
from time import sleep
import argparse


class OSCServerThread(Thread):
    def __init__(self, server: GradioOSCServer):
        super().__init__()
        self.server = server

    def run(self):
        self.server.serve_forever()

    def stop(self):
        self.server.shutdown()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--osc_port', type=int, default=10518,
                        help="osc server port")
    parser.add_argument('-d', '--gradio_dl', type=str, default=None,
                        help="gradio download folder")
    parser.add_argument('gradio_url', type=str,
                        help="gradio app url")
    return parser.parse_args()



def main():
    args = parse_args()

    print("*>* Hold on while we connect to your gradio app...")

    osc = GradioOSCServer(args.osc_port)
    osc.connect_gradio(args.gradio_url, download_dir=args.gradio_dl)

    thread = OSCServerThread(osc)
    print(f'OSC listening to port {args.osc_port}')
    thread.start()
    try:
        while True:
            sleep(1)
    except KeyboardInterrupt:
        thread.stop()
        thread.join()
        print("\nExiting...Bye!")
        exit(0)
    thread.join()
