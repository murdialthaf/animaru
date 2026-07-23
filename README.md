# Animaru

A GTK4 + Adwaita GUI for watching and downloading anime, powered by [anipy-api](https://github.com/anipy-org/anipy-api).

![screenshot](https://placehold.co/800x450/16142e/c8b8ff?text=Animaru)

## Features

- Browse trending, top-rated, and popular anime
- Search by title or browse by genre
- Episode lists with season selection
- Continue watching with progress tracking
- Watchlist management
- Dark theme (Adwaita forced dark)
- MPV integration for playback

## Installation

### Arch Linux (AUR)

```bash
yay -S animaru
# or
paru -S animaru
```

### pip (any distro)

```bash
pip install animaru
```

### From source

```bash
git clone https://github.com/murdialthaf/animaru.git
cd animaru
pip install .
```

## Dependencies

- **Python** ≥ 3.10
- **GTK4** + **libadwaita**
- **PyGObject** ≥ 3.56
- **anipy-api** ≥ 3.8
- **mpv** (for video playback)

On Arch Linux:

```bash
sudo pacman -S gtk4 libadwaita python-gobject mpv
```

## Usage

### From the terminal

```bash
animaru
```

### From the desktop

Search for "Animaru" in your application launcher.

### Configuration

Config is stored at `~/.config/animaru/config.json`:

```json
{
  "provider": "allanime",
  "quality": "1080",
  "player": "mpv",
  "download_dir": "~/Downloads/Animaru",
  "skip_intro": true
}
```

### Controls

- **Browse** — homepage rows for Trending, Top Rated, Popular, Recently Added
- **Search** — search bar at the top of the window
- **Genre** — browse by genre buttons
- **Play** — click an episode to play in mpv
- **Watchlist** — toggle from the detail view
- **Continue Watching** — auto-tracked episodes appear on the homepage

## License

GNU General Public License v3.0
