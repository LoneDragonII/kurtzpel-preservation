# tools/

Our own scripts: Frida hooks, capture parsers, pak listing and diff tools. Scripts take paths to
your local game builds and captures as arguments; they never ship game data.

| Path | What |
|---|---|
| `re/schema2019.py` | Prints a packet struct layout from a Deserialize function in the 2019 exe (capstone) |
| `re/handlers2019.py` | Maps each s2c packet name to its deserializer |
| `re/sends2019.py` | Maps c2s opcodes to their serializers |
| `frida/square_local.js` | 2019 client: open the Eltheca square locally instead of connecting to a square server |
