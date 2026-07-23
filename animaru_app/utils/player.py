import subprocess
import tempfile


def play_in_mpv(
    url: str,
    headers: dict[str, str] | None = None,
    title: str = "",
    chapters: str | None = None,
    start_time: float | None = None,
):
    cmd = ["mpv", f"--title={title}", url]

    if headers:
        for k, v in headers.items():
            cmd.insert(-1, f"--http-header-fields={k}: {v}")

    if chapters:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, prefix="animaru-chapters-"
        ) as f:
            f.write(chapters)
            chap_path = f.name
        cmd.insert(-1, f"--chapter-file={chap_path}")

    if start_time is not None:
        cmd.insert(-1, f"--start={start_time}")

    subprocess.run(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def stream_url(url: str, headers: dict[str, str] | None = None) -> str:
    if headers and "referer" in {k.lower(): k for k in headers}:
        ref = headers.get("Referer") or headers.get("referer", "")
        if ref:
            return f"http://{ref.split('://')[-1].split('/')[0]}/{url}"
    return url
