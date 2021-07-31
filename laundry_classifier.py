#!/usr/bin/env python3
#
# Copyright 2017 Google Inc.
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
"""Script to run generic MobileNet based classification model."""
import argparse

from picamera import PiCamera, Color

from aiy.vision import inference
from aiy.vision.models import utils

import requests


def read_labels(label_path):
    with open(label_path) as label_file:
        return [label.strip() for label in label_file.readlines()]


def get_message(result, threshold, top_k):
    if result:
        return 'Detecting:\n %s' % '\n'.join(result)

    return 'Nothing detected when threshold=%.2f, top_k=%d' % (threshold, top_k)


def process(result, labels, tensor_name, threshold, top_k):
    """Processes inference result and returns labels sorted by confidence."""
    # MobileNet based classification model returns one result vector.
    assert len(result.tensors) == 1
    tensor = result.tensors[tensor_name]
    probs, shape = tensor.data, tensor.shape
    assert shape.depth == len(labels)
    pairs = [pair for pair in enumerate(probs) if pair[1] > threshold]
    pairs = sorted(pairs, key=lambda pair: pair[1], reverse=True)
    pairs = pairs[0:top_k]
    return [' %s (%.2f)' % (labels[index], prob) for index, prob in pairs]

def process_winner(result, labels, tensor_name, threshold):
    """Processes inference result and returns the label with the highest confidence."""
    # MobileNet based classification model returns one result vector.
    assert len(result.tensors) == 1
    tensor = result.tensors[tensor_name]
    probs, shape = tensor.data, tensor.shape
    assert shape.depth == len(labels)
    pairs = [pair for pair in enumerate(probs) if pair[1] > threshold]
    pairs = sorted(pairs, key=lambda pair: pair[1], reverse=True)
    winner = pairs[0]
    # Adjusted to only return the label name of the winner
    return labels[winner[0]]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model_path', required=True,
        help='Path to converted model file that can run on VisionKit.')
    parser.add_argument('--label_path', required=True,
        help='Path to label file that corresponds to the model.')
    parser.add_argument('--input_height', type=int, required=True, help='Input height.')
    parser.add_argument('--input_width', type=int, required=True, help='Input width.')
    parser.add_argument('--input_layer', required=True, help='Name of input layer.')
    parser.add_argument('--output_layer', required=True, help='Name of output layer.')
    parser.add_argument('--num_frames', type=int, default=None,
        help='Sets the number of frames to run for, otherwise runs forever.')
    parser.add_argument('--input_mean', type=float, default=128.0, help='Input mean.')
    parser.add_argument('--input_std', type=float, default=128.0, help='Input std.')
    parser.add_argument('--input_depth', type=int, default=3, help='Input depth.')
    parser.add_argument('--threshold', type=float, default=0.1,
        help='Threshold for classification score (from output tensor).')
    parser.add_argument('--top_k', type=int, default=3, help='Keep at most top_k labels.')
    parser.add_argument('--preview', action='store_true', default=False,
        help='Enables camera preview in addition to printing result to terminal.')
    parser.add_argument('--show_fps', action='store_true', default=False,
        help='Shows end to end FPS.')
    args = parser.parse_args()

    model = inference.ModelDescriptor(
        name='mobilenet_based_classifier',
        input_shape=(1, args.input_height, args.input_width, args.input_depth),
        input_normalizer=(args.input_mean, args.input_std),
        compute_graph=utils.load_compute_graph(args.model_path))
    labels = read_labels(args.label_path)

    # Initialize counters
    sensing = 0
    rinse = 0

    with PiCamera(sensor_mode=4, resolution=(1640, 1232), framerate=30) as camera:
        if args.preview:
            camera.start_preview()

        with inference.CameraInference(model) as camera_inference:
            for result in camera_inference.run(args.num_frames):
                processed_result = process(result, labels, args.output_layer,
                                           args.threshold, args.top_k)

                # Added this to compute the alternative results tuple without probability score
                result_winner = process_winner(result, labels, args.output_layer,
                                           args.threshold)


                message = get_message(processed_result, args.threshold, args.top_k)
                if args.show_fps:
                    message += '\nWith %.1f FPS.' % camera_inference.rate

                # print(message)
                print(result_winner)

                if args.preview:
                    camera.annotate_foreground = Color('black')
                    camera.annotate_background = Color('white')
                    # PiCamera text annotation only supports ascii.
                    camera.annotate_text = '\n %s' % message.encode(
                        'ascii', 'backslashreplace').decode('ascii')

                # If 'sensing' is in the result_winner tuple
                ## Increment the sensing variable by 1
                if result_winner == 'sensing':
                    sensing += 1
                    print(sensing)

                # If 'rinse' is in the result_winner tuple
                ## Increment the rinse variable by 1
                if result_winner == 'rinse':
                    rinse += 1
                    print(rinse)

                # If the sensing variable is > 10
                if sensing == 10:
                 ## Sent a GET request to server
                    url = 'https://ide-e6a85d688f984a6fa579758e98ec5d79-8080.cs50.ws/sensing'
                    cookies = {'cs50_ws_dismiss_warning': '1', 'max-age': '5356800000', 'path'=: '/', 'samesite': 'None', 'secure',}
                    # Use python requests module to get related url and send cookies to it with cookies parameter. 
                    r = requests.get(url, cookies=cookies)
                    print(r)
                    sensing += 1
                    print(sensing)

                # If the rinse variable is > 10
                if rinse == 10:
                ## Sent a GET request to server
                    # Set url value.
                    url = 'https://ide-e6a85d688f984a6fa579758e98ec5d79-8080.cs50.ws/rinse'
                    # Create a dictionary object.
                    cookies = {'cs50_ws_dismiss_warning': '1', 'max-age': '5356800000', 'path': '/', 'samesite': 'None', 'secure',}
                    # Use python requests module to get related url and send cookies to it with cookies parameter. 
                    r = requests.get(url, cookies=cookies)
                    print(r)
                    rinse += 1
                    print(rinse)

        if args.preview:
            camera.stop_preview()


if __name__ == '__main__':
    main()
