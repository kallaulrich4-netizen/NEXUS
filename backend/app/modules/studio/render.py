"""
Rendu vidéo réel du Studio créatif — montage façon CapCut/InShot.

Gratuit et sans service tiers : utilise FFmpeg (déjà requis comme
dépendance système du projet, voir Dockerfile / deployment/deploy.sh),
qui tourne entièrement sur votre propre serveur.

Convention de `timeline_data` (JSON stocké dans `VideoProject.timeline_data`,
et validé au niveau schéma par studio/schemas.py) :

    {
      "clips": [
        {
          "type": "image" | "video" | "color",
          "media_id": "<uuid d'un StudioMediaAsset>",   # requis pour image/video
          "color": "black",                              # requis pour type "color"
          "duration_seconds": 3.0,                        # requis pour image/color ;
                                                            # optionnel pour video (coupe au besoin)
          "filter_id": "<uuid d'un Filter>",              # optionnel
          "text_overlay": "Bonjour !"                      # optionnel, incrusté en bas de l'image
        }
      ]
    }

`filter_id` référence la table `Filter` existante ; c'est sa `category`
(couleur, cinematique, vintage, noir_et_blanc, glow, correction, autre)
qui détermine l'effet visuel réellement appliqué (voir FILTER_CHAINS
ci-dessous — les mêmes grandes familles d'effets que CapCut/InShot :
noir & blanc, vintage/sépia, cinématique, vif/couleur, glow, correction
automatique).
"""
import subprocess
import uuid
from abc import ABC, abstractmethod
from pathlib import Path

# Chaînes de filtres FFmpeg par catégorie — équivalents simplifiés des
# familles d'effets qu'on retrouve dans CapCut/InShot. "autre"/inconnu
# n'applique aucun effet plutôt que d'échouer.
FILTER_CHAINS: dict[str, str] = {
    "noir_et_blanc": "hue=s=0",
    "vintage": "colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131,eq=contrast=1.05:saturation=0.85",
    "cinematique": "eq=contrast=1.15:saturation=0.85:brightness=-0.02,curves=preset=darker",
    "couleur": "eq=saturation=1.4:contrast=1.05",  # "vif" / couleurs saturées, popularisé par CapCut
    "glow": "gblur=sigma=4,eq=brightness=0.05",  # halo doux, approximation simple d'un effet glow
    "correction": "eq=contrast=1.05:brightness=0.02:saturation=1.1,unsharp=3:3:0.5",  # correction auto simple
    "autre": "",
}

# Police utilisée pour les incrustations de texte (drawtext). Plusieurs
# chemins candidats car ils varient selon la distribution Linux.
_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
]


class RenderError(Exception):
    """La vidéo n'a pas pu être générée (voir le message pour le détail)."""


class VideoRenderProvider(ABC):
    @abstractmethod
    def render(self, clips: list[dict], resolution: str, output_path: str) -> None:
        """
        Génère le fichier vidéo final à `output_path` à partir de `clips`
        (déjà résolus : chaque clip image/vidéo porte un `source_path`
        absolu sur le disque — la résolution `media_id` -> fichier se
        fait dans studio/service.py, pas ici). Lève RenderError en cas
        d'échec plutôt que de laisser une exception FFmpeg brute remonter.
        """
        raise NotImplementedError


class NotImplementedRenderProvider(VideoRenderProvider):
    """Conservé pour compatibilité ; non utilisé par défaut depuis l'ajout de FFmpegRenderProvider."""

    def render(self, clips: list[dict], resolution: str, output_path: str) -> None:
        raise RenderError("Le rendu vidéo n'est pas configuré sur ce serveur.")


def _find_font() -> str | None:
    for candidate in _FONT_CANDIDATES:
        if Path(candidate).is_file():
            return candidate
    return None


def _escape_drawtext(text: str) -> str:
    # FFmpeg drawtext a sa propre syntaxe d'échappement (: et ' notamment).
    return text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\u2019")


class FFmpegRenderProvider(VideoRenderProvider):
    """
    Rendu réel via des appels à l'exécutable `ffmpeg` (subprocess), sans
    bibliothèque Python supplémentaire. Approche : chaque clip est
    normalisé (résolution, cadence, filtres, texte) dans un segment
    temporaire, puis tous les segments sont concaténés en un seul fichier.
    """

    def __init__(self, ffmpeg_binary: str = "ffmpeg", fps: int = 30, timeout_seconds: int = 600):
        self._ffmpeg = ffmpeg_binary
        self._fps = fps
        self._timeout = timeout_seconds

    def render(self, clips: list[dict], resolution: str, output_path: str) -> None:
        if not clips:
            raise RenderError("La timeline ne contient aucun clip à assembler.")
        try:
            width, height = (int(part) for part in resolution.lower().split("x"))
        except (ValueError, AttributeError):
            raise RenderError(f"Résolution invalide : « {resolution} » (format attendu : LARGEURxHAUTEUR).")

        work_dir = Path(output_path).parent / f"_tmp_{uuid.uuid4()}"
        work_dir.mkdir(parents=True, exist_ok=True)
        try:
            segment_paths = []
            for index, clip in enumerate(clips):
                segment_path = work_dir / f"segment_{index:04d}.mp4"
                self._render_segment(clip, width, height, segment_path)
                segment_paths.append(segment_path)

            self._concatenate(segment_paths, work_dir, output_path)
        finally:
            for f in work_dir.glob("*"):
                f.unlink(missing_ok=True)
            work_dir.rmdir()

    def _build_video_filter(self, width: int, height: int, clip: dict) -> str:
        filters = [
            f"scale={width}:{height}:force_original_aspect_ratio=decrease",
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black",
        ]
        chain = FILTER_CHAINS.get(clip.get("filter_category") or "", "")
        if chain:
            filters.append(chain)

        text = clip.get("text_overlay")
        if text:
            font = _find_font()
            escaped = _escape_drawtext(text)
            drawtext = (
                f"drawtext=text='{escaped}':fontcolor=white:fontsize={max(18, height // 20)}"
                f":x=(w-text_w)/2:y=h-th-{max(20, height // 20)}"
                ":box=1:boxcolor=black@0.4:boxborderw=10"
            )
            if font:
                drawtext += f":fontfile='{font}'"
            filters.append(drawtext)

        return ",".join(filters)

    def _render_segment(self, clip: dict, width: int, height: int, segment_path: Path) -> None:
        clip_type = clip.get("type")
        duration = float(clip.get("duration_seconds") or 3.0)
        vf = self._build_video_filter(width, height, clip)

        if clip_type == "color":
            color = clip.get("color", "black")
            cmd = [
                self._ffmpeg, "-y", "-f", "lavfi",
                "-i", f"color=c={color}:s={width}x{height}:d={duration}:r={self._fps}",
                "-vf", vf, "-pix_fmt", "yuv420p", str(segment_path),
            ]
        elif clip_type == "image":
            source_path = clip.get("source_path")
            if not source_path or not Path(source_path).is_file():
                raise RenderError(f"Image source introuvable pour un clip ({clip.get('media_id')}).")
            cmd = [
                self._ffmpeg, "-y", "-loop", "1", "-i", source_path, "-t", str(duration),
                "-vf", vf, "-r", str(self._fps), "-pix_fmt", "yuv420p", str(segment_path),
            ]
        elif clip_type == "video":
            source_path = clip.get("source_path")
            if not source_path or not Path(source_path).is_file():
                raise RenderError(f"Vidéo source introuvable pour un clip ({clip.get('media_id')}).")
            cmd = [self._ffmpeg, "-y", "-i", source_path]
            if clip.get("duration_seconds"):
                cmd += ["-t", str(duration)]
            cmd += ["-vf", vf, "-r", str(self._fps), "-an", "-pix_fmt", "yuv420p", str(segment_path)]
        else:
            raise RenderError(f"Type de clip inconnu : « {clip_type} » (attendu : image, video, ou color).")

        self._run(cmd)

    def _concatenate(self, segment_paths: list[Path], work_dir: Path, output_path: str) -> None:
        if len(segment_paths) == 1:
            segment_paths[0].replace(output_path)
            return

        list_file = work_dir / "concat_list.txt"
        list_file.write_text(
            "\n".join(f"file '{p.resolve()}'" for p in segment_paths), encoding="utf-8"
        )
        cmd = [
            self._ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(list_file),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", str(output_path),
        ]
        self._run(cmd)

    def _run(self, cmd: list[str]) -> None:
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=self._timeout,
            )
        except subprocess.TimeoutExpired:
            raise RenderError("Le rendu a dépassé le délai maximal autorisé.")
        except FileNotFoundError:
            raise RenderError(
                "FFmpeg n'est pas installé sur ce serveur (commande 'ffmpeg' introuvable)."
            )
        if result.returncode != 0:
            # On garde seulement la fin du message d'erreur FFmpeg (souvent très long).
            raise RenderError(f"Échec FFmpeg : {result.stderr[-800:]}")


def get_render_provider() -> VideoRenderProvider:
    return FFmpegRenderProvider()
