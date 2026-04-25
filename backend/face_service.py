import io
import logging
import os

import numpy as np

logger = logging.getLogger(__name__)

# Attempt to import face_recognition; fall back gracefully so the module can
# still be imported in environments where dlib/face_recognition is not yet
# installed (e.g. during container build or CI).
try:
    import face_recognition as fr  # type: ignore

    _FR_AVAILABLE = True
except ImportError:  # pragma: no cover
    fr = None  # type: ignore
    _FR_AVAILABLE = False
    logger.warning(
        "face_recognition library not available. Face verification will be disabled."
    )

# Face match threshold — lower value = stricter matching.
# Typical range: 0.4 (very strict) to 0.6 (lenient).
# Default 0.5 is a good starting point; tune based on observed false-positive/
# negative rates for your student population and camera hardware.
FACE_MATCH_THRESHOLD = float(os.getenv("FACE_MATCH_THRESHOLD", "0.5"))


def encode_face_from_bytes(image_bytes: bytes) -> list[float] | None:
    """Decode an image from raw bytes and return the first face encoding found.

    Returns None if no face is detected or the library is unavailable.
    """
    if not _FR_AVAILABLE:
        return None

    try:
        import PIL.Image  # type: ignore

        img = PIL.Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img_array = np.array(img)
    except Exception as exc:  # pragma: no cover
        logger.error("Failed to decode image: %s", exc)
        return None

    encodings = fr.face_encodings(img_array)
    if not encodings:
        logger.info("No face detected in provided image.")
        return None

    return encodings[0].tolist()


def compare_faces(known_encoding_bytes: bytes, candidate_encoding: list[float]) -> tuple[bool, float]:
    """Compare a stored (serialised numpy array) encoding with a candidate encoding.

    Returns (match: bool, distance: float).
    """
    if not _FR_AVAILABLE:
        return False, 1.0

    try:
        known_array = np.frombuffer(known_encoding_bytes, dtype=np.float64)
        candidate_array = np.array(candidate_encoding, dtype=np.float64)

        distance = float(np.linalg.norm(known_array - candidate_array))
        match = distance <= FACE_MATCH_THRESHOLD
        return match, distance
    except Exception as exc:  # pragma: no cover
        logger.error("Error comparing face encodings: %s", exc)
        return False, 1.0


def encoding_to_bytes(encoding: list[float]) -> bytes:
    """Convert a face encoding (list of floats) to raw bytes for storage."""
    return np.array(encoding, dtype=np.float64).tobytes()


def validate_face_image(image_bytes: bytes) -> bool:
    """Return True if at least one face is detectable in the image."""
    if not _FR_AVAILABLE:
        return True  # allow in degraded mode

    encoding = encode_face_from_bytes(image_bytes)
    return encoding is not None
