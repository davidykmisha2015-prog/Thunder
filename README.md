# Thunder

![Logo](logo.png)

Thunder is a small experimental programming language for fast terminal and TUI applications.
The current release is **v0.1.0 MVP** and uses a lightweight Python interpreter.

## Features

- `.th` source files with brace-delimited blocks;
- variables, arithmetic, lists, and indexing;
- `if`, `else if`, `else`, `for`, and `while`;
- user functions with local scopes;
- `printt` and `printl`;
- file I/O with `read_file` and `write_file`;
- `import` for other `.th` modules;
- command-line arguments through `args`;
- external commands through `exec`;
- TUI primitives: `box`, `line`, `term_width`, and `term_height`;
- ANSI colors, text styles, Unicode borders, and UTF-8 output;
- readable `Thunder error` messages.

## Requirements

- Python 3.10 or newer;
- a terminal with UTF-8 support for Unicode TUI characters.

Thunder has no third-party runtime dependencies.

## Quick start

```powershell
python .\src\main.py .\examples\notebook.th
```

On Windows with the included virtual environment:

```powershell
.\.venv\Scripts\python.exe .\src\main.py .\examples\notebook.th
```

Pass arguments to a Thunder program after the source file:

```powershell
python .\src\main.py .\examples\args.th first.txt
```

Inside Thunder, the value is available as `args[0]`.

## Example

```th
main {
    box(36, 5, 2, 2, "cyan", "THUNDER", "center")

    i = 0
    while i < 3 {
        printt(i, "green", "bold")
        i = i + 1
    }

    line("horizontal", 30, 2, 8, "blue")
}
```

## Language overview

### Variables and expressions

```th
main {
    title = "Thunder OS"
    version = 1
    next = version + 1
    items = ["Home", "Settings", "Exit"]

    printt(items[0], "cyan")
}
```

### Conditions and loops

```th
main {
    if version == 1 {
        printt("MVP")
    } else if version > 1 {
        printt("New version")
    } else {
        printt("Unknown")
    }

    for i in range(3) {
        printt(i)
    }
}
```

### Functions and input

```th
fn greet(name) {
    printt(name, "green", "bold")
}

main {
    printl("Your name: ", name)
    greet(name)
}
```

See [`docs/language.md`](docs/language.md) for the complete v0.1 syntax reference.

## Project layout

```text
Thunder/
├── src/
│   ├── main.py      # interpreter entry point and frontend/runtime
│   └── tui.py       # terminal rendering implementation
├── thunder/         # lexer, parser, runtime, TUI API, and python -m entry point
├── examples/        # Thunder programs
├── docs/            # language documentation
├── test.th          # local development example
└── README.md
```

## Development checks

```powershell
.\.venv\Scripts\python.exe -m py_compile .\src\main.py .\src\tui.py .\thunder\*.py
.\.venv\Scripts\python.exe .\src\main.py .\examples\notebook.th --no-color
```

## Status

Thunder is an experimental MVP. The syntax and runtime API may change before a stable
release. Contributions and language design feedback are welcome.

## License

Thunder is released under the MIT License. See [`LICENSE`](LICENSE).
