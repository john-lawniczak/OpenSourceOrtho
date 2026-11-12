"""Compact face ownership preserves exact face identity for review and scoring."""
import base64
import numpy as np


def pack_face_labels(preview):
    for key, count_key, output_key in (
        ('source_faces', 'source_face_count', 'moving_face_labels_base64'),
        ('target_faces', 'target_face_count', 'target_face_labels_base64'),
    ):
        labels = np.zeros(preview[count_key], dtype=np.uint8)
        for index, tooth in enumerate(preview['teeth'], 1):
            faces = tooth.pop(key, None)
            if faces is not None and len(faces):
                if np.any(labels[faces]):
                    raise ValueError('Overlapping tooth regions')
                labels[faces] = index
            tooth['face_label'] = index
        preview[output_key] = base64.b64encode(labels.tobytes()).decode('ascii')
