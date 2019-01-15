#
# -*- coding: utf-8 -*-
#
# Copyright (c) 2019 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: EPL-2.0
#

"""Import a model graph and export a SavedModel.

Usage: model_graph_to_saved_model.py [--model_version=y] import_path export_dir
"""

from __future__ import print_function

import os
import sys

import tensorflow as tf
import tensorflow.tools.graph_transforms as graph_transforms

INPUTS = 'input'
OUTPUTS = 'predict'
OPTIMIZATION = 'strip_unused_nodes remove_nodes(op=Identity, op=CheckNumerics) fold_constants(ignore_errors=true) ' \
               'fold_batch_norms fold_old_batch_norms'

tf.app.flags.DEFINE_integer('model_version', 1, 'Version number of the model.')
tf.app.flags.DEFINE_string('import_path', '', 'Model import path.')
tf.app.flags.DEFINE_string('export_dir', '/tmp', 'Export directory.')
FLAGS = tf.app.flags.FLAGS


def main(_):
    if len(sys.argv) < 2 or sys.argv[-1].startswith('-'):
        print('Usage: model_graph_to_saved_model.py [--model_version=y] import_path export_dir')
        sys.exit(-1)
    if FLAGS.import_path == '':
        print('Please specify the path to the model graph you want to convert to SavedModel format.')
        sys.exit(-1)
    if FLAGS.model_version <= 0:
        print('Please specify a positive value for version number.')
        sys.exit(-1)

    # Import model graph
    with tf.Session() as sess:
        graph_def = tf.GraphDef()
        with tf.gfile.GFile(FLAGS.import_path, 'rb') as input_file:
            input_graph_content = input_file.read()
            graph_def.ParseFromString(input_graph_content)

        # Apply transform optimizations
        output_graph = graph_transforms.TransformGraph(graph_def, [INPUTS], [OUTPUTS], [OPTIMIZATION])
        sess.graph.as_default()
        tf.import_graph_def(output_graph, name='')

        # Build the signature_def_map.
        in_image = sess.graph.get_tensor_by_name('input:0')
        inputs = {INPUTS: tf.saved_model.utils.build_tensor_info(in_image)}

        out_classes = sess.graph.get_tensor_by_name('predict:0')
        outputs = {OUTPUTS: tf.saved_model.utils.build_tensor_info(out_classes)}

        signature = tf.saved_model.signature_def_utils.build_signature_def(
            inputs=inputs,
            outputs=outputs,
            method_name=tf.saved_model.signature_constants.PREDICT_METHOD_NAME
        )

        # Save out the SavedModel
        print('Exporting trained model to', FLAGS.export_dir + '/' + str(FLAGS.model_version))
        builder = tf.saved_model.builder.SavedModelBuilder(FLAGS.export_dir + '/' + str(FLAGS.model_version))
        builder.add_meta_graph_and_variables(
            sess, [tf.saved_model.tag_constants.SERVING],
            signature_def_map={
                tf.saved_model.signature_constants.DEFAULT_SERVING_SIGNATURE_DEF_KEY: signature
            }
        )
        builder.save()

    print('Done!')


if __name__ == '__main__':
    tf.app.run()
