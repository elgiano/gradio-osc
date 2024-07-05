from abc import ABC
import os
from shutil import move
from datetime import datetime


class GradioOSCFilter(ABC):
    '''
    Abstract base class for all filters.
    Filters can pre-process args before they are sent to gradio,
    and post-process results before they are sent to user.
    '''

    # extra_args are osc arguments used by filters but not by gradio
    extra_args = []

    def extract_inputs(self, gradio_args: dict) -> dict:
        '''
        Extract special args from inputs to prevent gradio from erroring due to unrecognized inputs.
        '''
        extracted = {}
        for k in self.extra_args:
            if k in gradio_args:
                extracted[k] = gradio_args[k]
                del gradio_args[k]
        return extracted

    def process_inputs(self, path: str, gradio_args: dict) -> dict:
        return self.extract_inputs(gradio_args)

    def process_outputs(self, path:str, special_args, results, replyAddr):
        pass


class FormatUploads(GradioOSCFilter):
    '''
    Filter to send OSC paths and have gradio-client to upload those files to gradio app.

    Some models accept file uploads (e.g. init_audio for diffusion or inpainting), and
    Gradio-client accepts string paths, but it will only upload files to gradio app
    if the args are provided as a dict like {path: str, meta: {_type: gradio.FileData}}.
    This filter makes gradio happy to upload files provided as string paths.
    '''

    def process_inputs(self, path: str, gradio_args: dict) -> dict:
        types = self.server.get_params_types(path)
        for k, v in gradio_args.items():
            if k in types and types[k] == "filepath":
                gradio_args[k] = { 
                    "path": v,
                    "meta": {"_type": "gradio.FileData"}
                }
        return {}


class MoveDownloads(GradioOSCFilter):
    '''
    Moves downloaded files to a named subdirectory,
    relative to the default download path used by gradio-client,
    and renames them as formattable filename (default: YYMMDD_HHMMSS.ext)
    osc-download_filename format:
        - date format codes: see https://docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes
        - %#: substituted with gradio hash
        - %n: substituted with download file number
        - %t: substituted with default timestamp YYMMDD_HHMMSS
    '''
    extra_args = ['osc-download_dirname', 'osc-download_filename']
    default_format = '%Y%m%d_%H%M%S'

    def __init__(self, verbose=False):
        self.verbose = verbose

    def process_inputs(self, path: str, gradio_args: dict):
        return super().extract_inputs(gradio_args)

    def process_outputs(self, path, special_args: dict, results, replyAddr):
        if all(arg not in special_args for arg in self.extra_args):
            return

        dst_dirname = special_args.get('osc-download_dirname', '')
        gradio_dl_path = self.server.gradio_client.download_files
        dst = os.path.join(gradio_dl_path, dst_dirname)

        filename_format = special_args.get('osc-download_filename', self.default_format)

        if not self.check_dstpath(dst, make=True):
            print(f"[MoveDownloads] Error: destination path '{dst}' doesn't exist")
            return

        types = self.server.get_results_types(path)
        for i, r in enumerate(results):
            if types[i] == 'filepath':
                # format filename
                hash = os.path.split(os.path.dirname(r))[-1]
                ext = os.path.splitext(r)[1]
                new_fname = filename_format.replace('%n', str(i))
                new_fname = filename_format.replace('%#', hash)
                new_fname = filename_format.replace('%t', '%Y%m%d_%H%M%S')
                new_fname = datetime.now().strftime(new_fname)
                new_path = os.path.join(dst, new_fname + ext)

                if self.verbose:
                    print(f"[MoveDownloads] moving {r}\n  -> {new_path}")
                move(r, new_path)
                # replace path in results
                results[i] = new_path

    def check_dstpath(self, dst, make=False):
        if not os.path.isdir(dst) and make:
            try:
                print(f"[MoveDownloads] creating path {dst}")
                os.makedirs(dst)
            except Exception as e:
                print(e)
        return os.path.isdir(dst)


class PrintDownloads(GradioOSCFilter):
    def process_outputs(self, path, special_args, results, replyAddr):
        types = self.server.get_results_types(path)
        for t, r in zip(types, results):
            print(f"📁 Downloaded {r}")

