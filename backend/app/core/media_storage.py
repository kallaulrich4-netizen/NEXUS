"""
Stockage local des fichiers médias (Studio : images/vidéos importées,
vidéos rendues). Gratuit, aucun service tiers requis : tout reste sur
le disque du serveur, sous `MEDIA_STORAGE_PATH` (.env).

En production à plus grande échelle, remplacez ce module par un vrai
stockage objet (S3, GCS, ou équivalent) si le volume ou la répartition
géographique des utilisateurs le justifie — l'appelant (studio/service.py)
ne connaît que les fonctions ci-dessous, jamais le détail du stockage,
même principe que AIProvider/PaymentProvider/VideoRenderProvider.
"""
import uuid
from pathlib import Path

from fastapi import UploadFile

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".mkv"}
ALLOWED_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS | ALLOWED_VIDEO_EXTENSIONS


class UnsupportedMediaTypeError(Exception):
    """Extension de fichier non autorisée."""


class MediaTooLargeError(Exception):
    """Fichier plus gros que la limite autorisée (MEDIA_MAX_UPLOAD_MB)."""


def _uploads_dir(base_path: str, owner_id: str) -> Path:
    path = Path(base_path) / "uploads" / owner_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def renders_dir(base_path: str) -> Path:
    path = Path(base_path) / "renders"
    path.mkdir(parents=True, exist_ok=True)
    return path


def media_type_for_extension(extension: str) -> str:
    if extension in ALLOWED_IMAGE_EXTENSIONS:
        return "image"
    if extension in ALLOWED_VIDEO_EXTENSIONS:
        return "video"
    raise UnsupportedMediaTypeError(
        f"Extension « {extension} » non autorisée. Formats acceptés : "
        f"{', '.join(sorted(ALLOWED_EXTENSIONS))}."
    )


def save_upload(base_path: str, owner_id: str, upload: UploadFile, max_size_bytes: int) -> tuple[str, str, str]:
    """
    Enregistre un fichier importé sur le disque local.
    Retourne (stored_filename, absolute_path, media_type).
    Lève UnsupportedMediaTypeError / MediaTooLargeError si invalide.
    """
    original_name = upload.filename or "fichier"
    extension = Path(original_name).suffix.lower()
    media_type = media_type_for_extension(extension)  # lève si non autorisé

    stored_filename = f"{uuid.uuid4()}{extension}"
    destination = _uploads_dir(base_path, owner_id) / stored_filename

    size = 0
    with open(destination, "wb") as f:
        while chunk := upload.file.read(1024 * 1024):
            size += len(chunk)
            if size > max_size_bytes:
                f.close()
                destination.unlink(missing_ok=True)
                raise MediaTooLargeError(
                    f"Fichier trop volumineux (limite : {max_size_bytes // (1024 * 1024)} Mo)."
                )
            f.write(chunk)

    return stored_filename, str(destination.resolve()), media_type


def delete_file(absolute_path: str) -> None:
    Path(absolute_path).unlink(missing_ok=True)
