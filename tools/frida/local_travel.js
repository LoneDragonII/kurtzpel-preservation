// Frida agent for the 2019-12-27 story client: play "server" maps locally.
// When the client travels to a game server (OpenLevel with an IP as the level name), open a map locally instead:
// the map named in the travel file (written by kzemu --travel-file for missions), else the Eltheca square.
// Usage: copy, set TRAVEL_FILE below, load with frida alongside the game. Build-specific RVAs.
'use strict';
const TRAVEL_FILE = '__TRAVEL_FILE__';
const SQUARE = '/Game/TheChase/Map/Eltheca/Square_Eltheca';
const base = Process.enumerateModules()[0].base;
const OpenLevel = base.add(0x144c2b0);           // UGameplayStatics::OpenLevel(ctx, FName, bool, FString)
const FNameCtor = new NativeFunction(base.add(0x618d40), 'pointer', ['pointer', 'pointer', 'int']);
const FNameToString = new NativeFunction(base.add(0x621290), 'pointer', ['pointer', 'pointer']);
function nameStr(v) {
  const tmp = Memory.alloc(8); tmp.writePointer(v);
  const out = Memory.alloc(16); FNameToString(tmp, out);
  const p = out.readPointer(); return p.isNull() ? '' : p.readUtf16String();
}
function target() {
  try {
    const t = File.readAllText(TRAVEL_FILE).trim();
    if (t) return t;
  } catch (e) {}
  return SQUARE;
}
Interceptor.attach(OpenLevel, {
  onEnter(a) {
    const name = nameStr(a[1]);
    send({ ev: 'OpenLevel', name });
    if (/^\d+\.\d+\.\d+\.\d+/.test(name)) {
      const to = target();
      const fn = Memory.alloc(8); FNameCtor(fn, Memory.allocUtf16String(to), 1);
      a[1] = fn.readPointer();
      send({ ev: 'OpenLevel-redirect', to });
    }
  }
});
