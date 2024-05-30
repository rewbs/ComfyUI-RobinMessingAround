import torch
from nodes import VAEEncode
import cv2
import os
import glob
import numpy as np
import logging
import tempfile

from .process_management import ProcessManager

class RobinsNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "audio_path": ("STRING", {"default": "/home/rewbs/temp-projectm-output"}),
                "preset_path": ("STRING", {"default": "/home/rewbs/temp-projectm-output"}),
                "beat_sensitivity": ("FLOAT", {"default": 2.0}),                
                "fps": ("INT", {"default": 24}),
                "width": ("INT", {"default": 1024}),
                "height": ("INT", {"default": 768}),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("images")
    FUNCTION = "projectm"
    CATEGORY = "examples"

    def __init__(self):
        self.logger = logging.Logger("RobinsNode")

    def projectm(self, audio_path, preset_path, fps, width, height):
        frames = []

        processManager = ProcessManager(self.logger)

        # start main generation process.
        output_dir = tempfile.TemporaryDirectory().name

        projectMCli_path = "projectMCli"
        projectM_proc = process_manager.run_process([projectMCli_path,
                                    "-a", audio_path,
                                    "-q", preset_path,
                                    "-o", output_dir,
                                    "--fps", str(fps),
                                    "--crf", "23"
                                    "--enableSplash=0",
                                    "--calibrate=1",
                                    "--outputType=both",
                                    "--width",  str(width),
                                    "--height", str(height),
                                    "--beatSensitivity", str(beat_sensitivity),
                                    "--texturePath=/app/textures/textures/"],
                                    cwd=output_dir,
                                    env={"EGL_PLATFORM":"surfaceless", "NVIDIA_DRIVER_CAPABILITIES":"all",  "LD_LIBRARY_PATH":f"/usr/local/lib/:{os.environ.get('LD_LIBRARY_PATH')}"},
                                    log_prefix="projectMCli")

        projectM_proc.wait()

        for file in glob.glob(os.path.join(output_diroutput_dir, "*.jpg")):
            frame = cv2.imread(file)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = np.array(frame, dtype=np.float32) / 255.0
            frame = torch.from_numpy(frame)
            frames.append(frame)


        if len(frames) == 0:
            raise FileNotFoundError(f"No images could be loaded from directory '{path}'.")

        # Stack frames along a new dimension (batch dimension) and ensure the correct shape
        result = torch.stack(frames)
        result = result.permute(3, 0, 1, 2)  # move batch dimension to front

        return result


class VAEDecodeBatched:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "samples": ("LATENT", ),
                "vae": ("VAE", ),
                "per_batch": ("INT", {"default": 16, "min": 1})
                }
            }
    
    CATEGORY = "Video Helper Suite 🎥🅥🅗🅢/batched nodes"

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "decode"

    def decode(self, vae, samples, per_batch):
        decoded = []
        for start_idx in range(0, samples["samples"].shape[0], per_batch):
            decoded.append(vae.decode(samples["samples"][start_idx:start_idx+per_batch]))
        return (torch.cat(decoded, dim=0), )




class VAEEncodeBatched:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "pixels": ("IMAGE", ), "vae": ("VAE", ),
                "per_batch": ("INT", {"default": 16, "min": 1})
                }
            }
    
    CATEGORY = "Video Helper Suite 🎥🅥🅗🅢/batched nodes"

    RETURN_TYPES = ("LATENT",)
    FUNCTION = "encode"

    def encode(self, vae, pixels, per_batch):
        t = []
        for start_idx in range(0, pixels.shape[0], per_batch):
            try:
                sub_pixels = vae.vae_encode_crop_pixels(pixels[start_idx:start_idx+per_batch])
            except:
                sub_pixels = VAEEncode.vae_encode_crop_pixels(pixels[start_idx:start_idx+per_batch])
            t.append(vae.encode(sub_pixels[:,:,:,:3]))
        return ({"samples": torch.cat(t, dim=0)}, )
