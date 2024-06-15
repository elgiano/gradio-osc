from abc import ABC
import os
from pathlib import Path
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

    def process_outputs(self, addr, path, special_args, results):
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
    Automatically move all downloaded files to osc-definable 'osc-download_path'.
    If the original download path is a subdirectory of gradio-client's default
    download folder (gradio_client.download_files), recreates subdirectories.
    e.g.
    osc-download_path: /home/foo/
    gradio's default: /tmp/gradio
    original download path: /tmp/gradio/1234567890/image.webp
    -> destination: /home/foo/123567890/image.webp
    '''
    extra_args = ['osc-download_path']

    def process_inputs(self, path: str, gradio_args: dict):
        return super().extract_inputs(gradio_args)

    def process_outputs(self, addr, path, special_args, results):
        if 'osc-download_path' not in special_args:
            return
        dst = special_args['osc-download_path']
        gradio_dl_path = self.server.gradio_client.download_files

        # check path, create only if parent already exists
        if not self.check_dstpath(dst,
                                  make=os.path.exists(Path(dst).parent)):
            print(f"[MoveDownloads] Error: destination path '{dst}' doesn't exist")
            return

        types = self.server.get_results_types(path)
        for i, r in enumerate(results):
            if types[i] == 'filepath':
                new_path = self.get_dstpath(r, dst, gradio_dl_path)
                print(f"[MoveDownloads] moving {r}\n  -> {new_path}")
                move(r, new_path)
                # replace path in results
                results[i] = new_path

    def check_dstpath(self, dst, make=False):
        if not os.path.isdir(dst) and make:
            try:
                os.makedirs(dst)
            except Exception as e:
                print(e)
        return os.path.isdir(dst)

    def get_dstpath(self, orig, dst, orig_root):
        if os.path.commonpath([orig, orig_root]) == orig_root:
            # if orig is in a subdir of gradio_download_path
            # recreate eventual gradio_download_path subdir
            path = os.path.join(dst, os.path.relpath(orig, orig_root))
            os.makedirs(os.path.dirname(path), exist_ok=True)
            return path
        else:
            return os.path.join(dst, os.path.basename(orig))


class RenameFiles(MoveDownloads):
    '''
    Moves download files to 'osc-download_dirname', relative to GRADIO_DOWNLOAD_FILES
    and renames them as timestamp YYMMDD_HHMMSS.ext
    '''
    extra_args = ['osc-download_dirname']

    def process_inputs(self, path: str, gradio_args: dict):
        special_args = super().extract_inputs(gradio_args)
        # save prompt for later
        return special_args

    def process_outputs(self, addr, path, special_args, results):
        if 'osc-download_dirname' not in special_args:
            return
        dst = special_args['osc-download_dirname']
        gradio_dl_path = self.server.gradio_client.download_files

        dst = os.path.join(gradio_dl_path, dst)

        # check path, create only if parent already exists
        if not self.check_dstpath(dst,
                                  make=os.path.exists(Path(dst).parent)):
            print(f"[MoveDownloads] Error: destination path '{dst}' doesn't exist")
            return

        types = self.server.get_results_types(path)
        for i, r in enumerate(results):
            if types[i] == 'filepath':
                new_path = self.get_dstpath(r, dst, gradio_dl_path)
                print(f"[MoveDownloads] moving {r}\n  -> {new_path}")
                move(r, new_path)
                # replace path in results
                results[i] = new_path

    def get_dstpath(self, orig, dst, orig_root):
        ext = os.path.splitext(orig)[1]
        return os.path.join(dst, self.get_timestamp()+ext)

    def get_timestamp(self):
        return datetime.now().strftime('%Y%m%d_%H%M%S')
