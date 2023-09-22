# PREREQUISITES:
# 1. Create a modal secret group
#   HUGGINGFACE_TOKEN = <your huggingface token>
#   with name "huggingface"
# 2. Create a modal secret group
#   MYTHALION_API_KEY = <generate a random key>
#   with name "ext-api-key"
# 3. modal deploy

from os import environ
from modal import Image, Secret, Stub
from modal import gpu, Secret

import vllm_runner.shared.utils as utils
import vllm_runner.shared.config as config

# MODEL = "Undi95/ReMM-SLERP-L2-13B"
# MODEL = "Gryphe/MythoMax-L2-13b"


env = {
    "RUNNER_NAME": __name__,
    "RUNNER_MODEL": "Gryphe/MythoMax-L2-13b",
    "RUNNER_MODEL_PATH": "/model",
    "API_KEY_ID": "MYTHOMAX_API_KEY",
    "HF_HUB_ENABLE_HF_TRANSFER": "1",
}

concurrent_inputs = 12

stub = Stub(env["RUNNER_NAME"])

# image = (
#     Image.from_registry("nvcr.io/nvidia/pytorch:22.12-py3")
#     .pip_install("torch==2.0.1", index_url="https://download.pytorch.org/whl/cu118")
#     # Pinned to 08/15/2023
#     .pip_install(
#         "vllm @ git+https://github.com/vllm-project/vllm.git@805de738f618f8b47ab0d450423d23db1e636fa2",
#         "typing-extensions==4.5.0",  # >=4.6 causes typing issues
#     )
#     # Use the barebones hf-transfer package for maximum download speeds. No progress bar, but expect 700MB/s.
#     .pip_install("hf-transfer~=0.1")
#     .env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})
#     .run_function(
#         download,
#         secret=Secret.from_name("huggingface"),
#         timeout=60 * 20,
#     )
# )

stub.gpu_image = (
    Image.from_registry("nvcr.io/nvidia/pytorch:22.12-py3")
    .pip_install(
        "vllm == 0.1.7",
        # Pinned to Sep/11/2023
        # "vllm @ git+https://github.com/vllm-project/vllm.git@b9cecc26359794af863b3484a3464108b7d5ee5f",
        # Pinned to 08/15/2023
        # "vllm @ git+https://github.com/vllm-project/vllm.git@805de738f618f8b47ab0d450423d23db1e636fa2",
        "typing-extensions==4.5.0",  # >=4.6 causes typing issues
    )
    # Use the barebones hf-transfer package for maximum download speeds. No progress bar, but expect 700MB/s.
    .pip_install("hf-transfer~=0.1")
    .env(env)
    .run_function(
        utils.download_model,
        secret=Secret.from_name("huggingface"),
        timeout=60 * 20,
    )
)

stub.cpu_image = Image.debian_slim().env(env)

from vllm_runner.shared.gpu_model import Model


stub.cls(
    image=stub.gpu_image,
    gpu=gpu.A100(),
    secret=Secret.from_name("huggingface"),
    allow_concurrent_inputs=concurrent_inputs,
    container_idle_timeout=600,
    keep_warm=config.keep_warm,
)(Model)


from vllm_runner.shared.cpu_endpoint import completion

stub.function(
    image=stub.cpu_image,
    secret=Secret.from_name("ext-api-key"),
    timeout=60 * 60,
    allow_concurrent_inputs=concurrent_inputs,
    keep_warm=config.keep_warm,
)(completion)