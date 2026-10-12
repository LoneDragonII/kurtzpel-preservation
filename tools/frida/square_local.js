// Frida agent (2019-12-27 story exe): when the client travels to the square server (OpenLevel with an IP as the
// level name), open Square_Eltheca locally instead, so the player walks around their own copy of the square.
'use strict';
const base = Process.enumerateModules()[0].base;
const OpenLevel = base.add(0x144c2b0);           // UGameplayStatics::OpenLevel(ctx, FName, bool, FString)
const FNameCtor = new NativeFunction(base.add(0x618d40), 'pointer', ['pointer', 'pointer', 'int']);
const FNameToString = new NativeFunction(base.add(0x621290), 'pointer', ['pointer', 'pointer']);
const target = Memory.allocUtf16String('/Game/TheChase/Map/Eltheca/Square_Eltheca');
function nameStr(v) {
  const tmp = Memory.alloc(8); tmp.writePointer(v);
  const out = Memory.alloc(16); FNameToString(tmp, out);
  const p = out.readPointer(); return p.isNull() ? '' : p.readUtf16String();
}
Interceptor.attach(OpenLevel, {
  onEnter(a) {
    const name = nameStr(a[1]);
    let opts = '';
    try { const p = a[3].readPointer(); if (!p.isNull()) opts = p.readUtf16String(); } catch (e) {}
    send({ ev: 'OpenLevel', name, opts });
    if (/^\d+\.\d+\.\d+\.\d+/.test(name)) {
      const fn = Memory.alloc(8); FNameCtor(fn, target, 1);
      a[1] = fn.readPointer();
      send({ ev: 'OpenLevel-redirect', to: 'Square_Eltheca (local)' });
    }
  }
});
