# -*- coding: utf-8 -*-
# Copyright 2019 The Blueoil Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =============================================================================
import os
from pathlib import Path
import tempfile

import pytest

from blueoil.cmd.convert import convert
from blueoil.cmd.predict import predict
from blueoil.cmd.train import train
from blueoil import environment
from blueoil.utils.config import load


@pytest.fixture
def init_env():
    """Initialize blueoil environment"""
    blueoil_dir = str(Path('{}/../../../'.format(__file__)).resolve())
    config_dir = os.path.join(blueoil_dir, 'tests/fixtures/configs')

    train_output_dir = os.path.join(blueoil_dir, 'tmp')
    predict_output_dir = tempfile.TemporaryDirectory()

    environment_originals = {}
    environ_originals = {}

    # TODO: Remove this setting after blueoil.environment has been refactored.
    envs = {
        "DATA_DIR": os.path.join(blueoil_dir, "tests", "unit", "fixtures", "datasets"),
        "OUTPUT_DIR": train_output_dir,
        "_EXPERIMENT_DIR": os.path.join(train_output_dir, "{experiment_id}"),
        "_TENSORBOARD_DIR": os.path.join(train_output_dir, "{experiment_id}", "tensorboard"),
        "_CHECKPOINTS_DIR": os.path.join(train_output_dir, "{experiment_id}", "checkpoints"),
    }

    for k, v in envs.items():
        environment_originals[k] = getattr(environment, k)
        environ_originals[k] = os.environ.get(k)
        setattr(environment, k, v)
        os.environ[k] = v

    yield {
        "train_output_dir": train_output_dir,
        "predict_output_dir": predict_output_dir.name,
        "blueoil_dir": blueoil_dir,
        "config_dir": config_dir,
    }

    for k, v in environment_originals.items():
        setattr(environment, k, v)
    for k, v in environ_originals.items():
        if v is not None:
            os.environ[k] = v
        else:
            del os.environ[k]

    predict_output_dir.cleanup()


def run_all_steps(dirs, config_file):
    """
    Test of the following steps.

    - Train using given config.
    - Convert using training result.
    - Predict using training result.
    """
    config_path = os.path.join(dirs["config_dir"], config_file)
    config = load(config_path)

    # Train
    experiment_id, checkpoint_name = train(config_path)

    train_output_dir = os.path.join(dirs["train_output_dir"], experiment_id)
    assert os.path.exists(os.path.join(train_output_dir, 'checkpoints'))

    # Convert
    convert(experiment_id)

    convert_output_dir = os.path.join(train_output_dir, 'export', checkpoint_name)
    lib_dir = os.path.join(
        convert_output_dir,
        "{}x{}".format(config.IMAGE_SIZE[0], config.IMAGE_SIZE[1]),
        'output',
        'models',
        'lib',
    )
    assert os.path.exists(os.path.join(lib_dir, 'lm_aarch64.elf'))
    assert os.path.exists(os.path.join(lib_dir, 'lm_aarch64_fpga.elf'))
    assert os.path.exists(os.path.join(lib_dir, 'lm_arm.elf'))
    assert os.path.exists(os.path.join(lib_dir, 'lm_arm_fpga.elf'))
    assert os.path.exists(os.path.join(lib_dir, 'lm_x86.elf'))
    assert os.path.exists(os.path.join(lib_dir, 'lm_x86_avx.elf'))

    assert os.path.exists(os.path.join(lib_dir, 'libdlk_aarch64.so'))
    assert os.path.exists(os.path.join(lib_dir, 'libdlk_aarch64_fpga.so'))
    assert os.path.exists(os.path.join(lib_dir, 'libdlk_arm.so'))
    assert os.path.exists(os.path.join(lib_dir, 'libdlk_arm_fpga.so'))
    assert os.path.exists(os.path.join(lib_dir, 'libdlk_x86.so'))
    assert os.path.exists(os.path.join(lib_dir, 'libdlk_x86_avx.so'))

    assert os.path.exists(os.path.join(lib_dir, 'libdlk_aarch64.a'))
    assert os.path.exists(os.path.join(lib_dir, 'libdlk_aarch64_fpga.a'))
    assert os.path.exists(os.path.join(lib_dir, 'libdlk_arm.a'))
    assert os.path.exists(os.path.join(lib_dir, 'libdlk_arm_fpga.a'))
    assert os.path.exists(os.path.join(lib_dir, 'libdlk_x86.a'))
    assert os.path.exists(os.path.join(lib_dir, 'libdlk_x86_avx.a'))

    # Predict
    predict_input_dir = os.path.join(dirs["blueoil_dir"], "tests/unit/fixtures/sample_images")
    predict_output_dir = dirs["predict_output_dir"]
    predict(predict_input_dir, predict_output_dir, experiment_id, checkpoint=checkpoint_name)

    assert os.path.exists(os.path.join(predict_output_dir, 'images'))
    assert os.path.exists(os.path.join(predict_output_dir, 'json', '0.json'))
    assert os.path.exists(os.path.join(predict_output_dir, 'npy', '0.npy'))
