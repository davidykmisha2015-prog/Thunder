# Thunder v0.1 language reference

Every source file uses the `.th` extension and starts with a named block:

```th
main {
    printt("Hello, Thunder!")
}
```

## Values

Thunder supports strings, integers, floating-point numbers, booleans, lists,
variables, arithmetic expressions, and list indexing.

```th
main {
    enabled = true
    count = 2
    labels = ["One", "Two"]
    printt(labels[0])
}
```

## Control flow

```th
if condition {
    # statements
} else if another_condition {
    # statements
} else {
    # statements
}

for i in range(3) {
    printt(i)
}

while count > 0 {
    count = count - 1
}
```

Logical operators are `and`, `or`, and `not`. Comparisons include `==`, `!=`,
`>`, `<`, `>=`, and `<=`.

## Functions

```th
fn show(title) {
    printt(title, "cyan", "bold")
}

main {
    show("Menu")
}
```

Function assignments are local. Functions can read variables from an outer
scope, but local assignments do not overwrite the outer value.

## Built-ins

| Built-in | Description |
| --- | --- |
| `printt(value)` | Print plain text |
| `printt(value, color)` | Print colored text |
| `printt(value, color, style)` | Print styled text |
| `printl(prompt, variable)` | Read input into a variable |
| `read_file(path)` | Read UTF-8 text |
| `write_file(path, text)` | Write UTF-8 text |
| `exec(command)` | Run a shell command and return stdout |
| `term_width()` | Read terminal width |
| `term_height()` | Read terminal height |
| `box(w, h, x, y, color, text, align)` | Draw a TUI box |
| `line(direction, length, x, y, color)` | Draw a horizontal/vertical line |

Supported colors include `black`, `red`, `green`, `yellow`, `blue`, `magenta`,
`cyan`, and `white`. Text styles include `bold`, `italic`, `underline`, and
`inverse`.

## Modules and arguments

Import a sibling `.th` file without the extension:

```th
import ui_helpers
```

Command-line arguments are available through `args`:

```th
main {
    printt(args[0])
}
```

## Comments and errors

Comments start with `#` and continue to the end of the line. Syntax and runtime
failures are reported as `Thunder error` messages instead of raw Python traces.
