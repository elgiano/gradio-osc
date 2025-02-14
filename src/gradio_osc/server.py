from gradio_client import Client
from pythonosc.osc_server import BlockingOSCUDPServer, Dispatcher
from pythonosc.udp_client import SimpleUDPClient
from typing import Tuple

from .filters import FormatUploads, MoveDownloads, PrintDownloads


class GradioOSCServer(BlockingOSCUDPServer):

    def __init__(self, port, host="localhost", filters=[]):
        super().__init__((host, port), Dispatcher())
        self.dispatcher.set_default_handler(self.osc_handler,
                                            needs_reply_address=True)
        self.filters = [
            FormatUploads(),
            MoveDownloads(),
            PrintDownloads()
        ] + filters
        for f in self.filters:
            f.server = self
        # self.progress_monitor = ProgressMonitor()

    def connect_gradio(self, gradio_src, download_dir=None, **gradio_kwargs):
        # add download_dir to gradio_kwargs only if not None
        # so to allow Client to set it's DEFAULT_TMP_DIR if download_dir=None
        if download_dir is not None:
            gradio_kwargs['download_files'] = download_dir
        self.gradio_client = Client(gradio_src, **gradio_kwargs)
        api_dict = self.gradio_client.view_api(return_format="dict")
        self.gradio_endpoints = api_dict["named_endpoints"]
        # print_gradio_api(api_dict)

    def get_endpoint(self, path: str, print_error=True):
        if self.gradio_endpoints is None:
            if print_error:
                print("ERROR: gradio_endpoints not loaded")
            return None
        if path not in self.gradio_endpoints:
            if print_error:
                print(f"ERROR: endpoint {path} not found in gradio")
            return None
        return self.gradio_endpoints[path]

    def get_params_spec(self, path: str, print_error=True):
        endpoint = self.get_endpoint(path, print_error=print_error)
        return endpoint['parameters'] if endpoint is not None else None

    def get_params_types(self, path: str, print_error = True):
        specs = self.get_params_spec(path, print_error)
        types = {}
        if specs is None:
            return types
        for s in specs:
            types[s['parameter_name']] = s['python_type']['type']
        return types

    def get_results_spec(self, path: str, print_error=True):
        endpoint = self.get_endpoint(path, print_error=print_error)
        return endpoint['returns'] if endpoint is not None else None

    def get_results_types(self, path: str, print_error=True):
        specs = self.get_results_spec(path, print_error)
        if specs is None:
            return []
        return [s['python_type']['type'] for s in specs]

    def osc_handler(self, replyAddr: Tuple[str, int], path: str, *args):
        print(f"\n> New job received: {path}")
        print(args)
        if self.get_endpoint(path, print_error=True) is None:
            return

        # turn args from ["key", "value", ...] to a kwargs dict
        gradio_args = dict(zip(args[0::2], args[1::2]))

        # process special args
        if 'osc-reply_host' in gradio_args:
            replyAddr = (gradio_args['osc-reply_host'], replyAddr[1])
            del gradio_args['osc-reply_host']
        if 'osc-reply_port' in gradio_args:
            replyAddr = (replyAddr[0], gradio_args['osc-reply_port'])
            del gradio_args['osc-reply_port']

        filter_args = self.filter_inputs(path, gradio_args)
        # print(gradio_args)

        self.gradio_client.submit(api_name=path, result_callbacks=[
            lambda *results: self.reply_results(replyAddr, path, filter_args, results)
        ], **gradio_args)
        print("job submitted to gradio app...")

        # self.progress_monitor.add_job(job)
        # self.reply_status(replyAddr, job)

    def filter_inputs(self, path, gradio_args):
        filter_args = []
        for filter in self.filters:
            args = None
            try:
                args = filter.process_inputs(path, gradio_args)
            except Exception as e:
                print("Error filtering inputs:")
                print(e)
            finally:
                filter_args.append(args)
        return filter_args

    def reply_results(self, replyAddr: Tuple[str, int],
                      path: str, filter_args: list, results):
        # convert from tuple to list, so that filters can alter results
        # (a tuple can't be modified)
        print("\ngot results from gradio")
        results = list(results)
        for (filter, f_args) in zip(self.filters, filter_args):
            try:
                filter.process_outputs(path, f_args, results, replyAddr)
            except Exception as e:
                print("Error filtering results:")
                print(e)

        osc_args = self.results_to_osc_args(results)
        print(f"👍 Job Done! sending reply to {replyAddr}")
        SimpleUDPClient(replyAddr[0], replyAddr[1]).send_message(
            path + ".reply",
            osc_args)

    def results_to_osc_args(self, returns):
        '''
        Convert gradio results to osc-compatible args.
        Currently only expands lists and stringifies dicts.
        '''
        def convert(obj):
            if type(obj) is list:
                return [convert(o) for o in obj]
            elif type(obj) is dict:
                return str(obj)
            else:
                return obj
        return [convert(r) for r in returns]

    # def reply_status(self, addr: Tuple[str, int], job):
    #     job_id = self.jobs.get_id(job)
    #     print("JOB ID:", job_id, job.status())
    #     SimpleUDPClient(addr[0], addr[1]).send_message("/gradio-osc/job.status",

    # note: leaving job canceling for later
    # 1. apparently you can't cancel already running jobs?
    # 2. gradio seems to run multiple jobs concurrently!
    # 3. I get strange Future errors
    # def shutdown(self):
        # for job_id, job in self.jobs.items():
        #     print("Canceling job", job_id, job.status())
        #     job.cancel()
        # self.progress_monitor.stop()
        # self.progress_monitor.join()
        # super().shutdown()

    # def serve_forever(self):
        # self.progress_monitor.start()
        # super().serve_forever()


# note: apparently we don't get progress info from gradio...
# only thing we get is a status update between QUEUED, PROCESSING and FINISHED
# but then it's pointless to monitor progress here, we can just get a reply when done
# https://www.gradio.app/docs/python-client/job
# "If the event handler does not have a gr.Progress() tracker, the progress_data field will be None"
# class ProgressMonitor(Thread):
#     def __init__(self):
#         super().__init__()
#         self.running = False
#         self.jobs = dict()

#     def add_job(self, job):
#         id = hash(job)
#         self.jobs[id] = job
#         return id

#     def get_id(self, job):
#         id = hash(job)
#         return id if id in self else None

#     def run(self):
#         self.running = True
#         while self.running:
#             for job_id, job in self.jobs.items():
#                 print("progress", job_id, job.status())
#             sleep(1)

#     def stop(self):
#         self.running = False
