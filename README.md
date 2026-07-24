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

### pipx (any distro)

Install pipx first if you don't have it:

```bash
# Arch Linux
sudo pacman -S python-pipx

# Debian/Ubuntu
sudo apt install pipx && pipx ensurepath
```

Then install Animaru:

```bash
pipx install git+https://github.com/murdialthaf/animaru.git
```

## Dependencies

On Arch Linux:

```bash
sudo pacman -S gtk4 libadwaita python-gobject mpv
```

Dependencies pulled automatically by pip (source/pipx installs):
- **anipy-api** ≥ 3.8
- **PyGObject** ≥ 3.56

## Usage

```bash
animaru
```

Or search for "Animaru" in your application launcher.

## Configuration

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

## Controls

- **Browse** — homepage rows for Trending, Top Rated, Popular, Recently Added
- **Search** — search bar at the top of the window
- **Genre** — browse by genre buttons
- **Play** — click an episode to play in mpv
- **Watchlist** — toggle from the detail view
- **Continue Watching** — auto-tracked episodes appear on the homepage

## License

GNU General Public License v3.0
