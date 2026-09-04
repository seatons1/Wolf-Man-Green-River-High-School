# Wolf-Man — Green River High School

Wolf-Man is a Pac-Man-style educational arcade game built with Python,
Pygame Community Edition, and Pygbag for browser play.

## Play

The browser version is published with GitHub Pages. The game supports
keyboard controls and is designed to run on modern desktop and mobile
browsers that support WebAssembly.

### Controls

- Arrow keys or WASD — move the wolf
- Space — play again after the end screen
- Enter — exit/stop the game
- Eat all 10 tigers to win
- The wolf has 3 lives

## Local development

Install Pygame Community Edition and Pygbag:

```bash
python -m pip install pygame-ce pygbag
```

From this folder:

```bash
python -m pygbag .
```

Then open the local address shown by Pygbag (normally `http://localhost:8000`).

For a deployment build:

```bash
python -m pygbag --build .
```

Pygbag places the deployable browser files in `build/web/`.

## GitHub Pages

This repository includes a GitHub Actions workflow that builds the Pygbag
web version and deploys `build/web/` to GitHub Pages whenever changes are
pushed to `main`.

## Open-source note

The Python game code is released under the MIT License.

The included mascot artwork, school branding, and music are separate assets
and may have their own copyright/trademark restrictions. They are not
automatically relicensed by the MIT license. Review the rights for any
asset before redistributing it outside its intended school/project use.

## Credits

Created as a Green River High School computer-science project.
