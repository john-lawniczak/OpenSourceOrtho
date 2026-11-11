import base64
import pytest

np = pytest.importorskip("numpy")
pydicom = pytest.importorskip("pydicom")
from orthoplan.imaging.dicom_volume import build_review_packet  # noqa:E402
from orthoplan.volume_coordinates import patient_point, patient_centerline, validate_voxel_affine  # noqa:E402


def write_series(root, missing=False):
    from pydicom.dataset import FileDataset, FileMetaDataset
    from pydicom.uid import ExplicitVRLittleEndian, CTImageStorage, generate_uid

    uid = generate_uid()
    for i in range(4):
        meta = FileMetaDataset()
        meta.TransferSyntaxUID = ExplicitVRLittleEndian
        meta.MediaStorageSOPClassUID = CTImageStorage
        meta.MediaStorageSOPInstanceUID = generate_uid()
        path = root / f"{3 - i}.dcm"
        ds = FileDataset(str(path), {}, file_meta=meta, preamble=bytes(128))
        ds.SeriesInstanceUID = uid
        ds.Rows = 8
        ds.Columns = 8
        ds.ImageOrientationPatient = [0, 1, 0, -1, 0, 0]
        ds.ImagePositionPatient = [10, 20, 30 + (i + int(missing and i > 1)) * 2]
        ds.PixelSpacing = [0.5, 0.25]
        ds.SamplesPerPixel = 1
        ds.PhotometricInterpretation = "MONOCHROME2"
        ds.BitsAllocated = 16
        ds.BitsStored = 16
        ds.HighBit = 15
        ds.PixelRepresentation = 0
        ds.RescaleSlope = 2
        ds.RescaleIntercept = -10
        ds.PatientName = "DO NOT EXPORT"
        ds.PixelData = np.full((8, 8), i, dtype="<u2").tobytes()
        ds.save_as(path, enforce_file_format=True)


def test_series_sort_rescale_and_patient_affine(tmp_path):
    write_series(tmp_path)
    packet = build_review_packet(tmp_path, stride=2)
    assert packet["dimensions_xyz"] == [4, 4, 2]
    pixels = np.frombuffer(base64.b64decode(packet["pixels_base64"]), dtype="<f4").reshape(2, 4, 4)
    assert pixels[0, 0, 0] == -10 and pixels[1, 0, 0] == -6
    matrix = packet["voxel_to_patient_mm"]
    validate_voxel_affine(matrix)
    assert patient_point([1, 2, 1], packet["voxel_spacing_mm"], matrix) == (8, 20.5, 34)
    assert "PatientName" not in packet and "DO NOT EXPORT" not in str(packet)
    assert packet["source_slices"] == 4


def test_missing_slices_are_rejected_and_rotated_centerline_is_not_z_dependent(tmp_path):
    write_series(tmp_path, missing=True)
    with pytest.raises(ValueError, match="missing"):
        build_review_packet(tmp_path)
    points = [(x, 10, 20) for x in range(20)]
    line = patient_centerline(points)
    assert len(line) > 2 and line[-1][0] > line[0][0]
    assert all(p[1:] == (10, 20) for p in line)


def test_landmark_proposal_has_independent_residuals_and_remains_unaccepted():
    pytest.importorskip("scipy")
    from orthoplan.imaging.landmark_registration import landmark_proposal

    source = np.array([[0, 0, 0], [3, 0, 0], [0, 4, 0], [0, 0, 5], [2, 2, 2]], dtype=float)
    packet = dict(
        schema="ortho-landmark-pairs-v1",
        units="mm",
        source_points_mm=source.tolist(),
        target_points_lps_mm=(source + [10, 20, 30]).tolist(),
        registration_id="r",
        source_stl_asset_id="s",
        target_cbct_record_id="v",
        source_scan_sha256="a" * 64,
        volume_source_digest="b" * 64,
    )
    result = landmark_proposal(packet)
    assert result["registration"]["accepted"] is False
    assert result["max_held_out_mm"] < 1e-10
    np.testing.assert_allclose(np.array(result["registration"]["matrix"])[:3, 3], [10, 20, 30])
    packet["target_points_lps_mm"][0][0] += 2
    assert landmark_proposal(packet)["max_held_out_mm"] > 1
