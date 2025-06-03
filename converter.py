"""
Lottie `.tgs` to image conversion logic.
"""
import subprocess
from lottie import parsers
from loguru import logger
from typing import Optional


def tgs_convert(
    tgs_path: str,
    target_path: str,
    width: Optional[int] = None,
    height: Optional[int] = None,
    fps: int = 60,
    quality: int = 100,
    script_path: str = None,
) -> None:
    """
    Convert a `.tgs` file to a specified image format using an external shell script.

    :param tgs_path: Path to the source `.tgs` file.
    :param target_path: Path for the output image file.
    :param width: Desired width of the output (defaults to original width).
    :param height: Desired height of the output (defaults to original height).
    :param fps: Frame rate to use.
    :param quality: Output quality (percentage).
    :param script_path: Path to the conversion script (e.g., `lottie_to_gif.sh`).
    :raises subprocess.CalledProcessError: If the conversion script fails.
    """
    animation = parsers.tgs.parse_tgs(tgs_path)
    if fps:
        animation.frame_rate = fps

    if width is None:
        width = animation.width
    if height is None:
        height = animation.height

    cmd = [
        "bash",
        script_path,
        "--output", str(target_path),
        "--height", str(height),
        "--width", str(width),
        "--fps", str(fps),
        "--quality", str(max(1, min(quality, 100))),
        tgs_path,
    ]
    logger.info(f"Running conversion command: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)