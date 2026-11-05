import { describe, expect, it, vi } from "vitest";

import { createNavigator, isPlainLeftClick } from "./navigation";

function fakeBrowser(initialPath: string) {
  let path = initialPath;
  let popStateListener: (() => void) | null = null;
  const history = {
    pushState: vi.fn((_data: unknown, _unused: string, url: string) => {
      path = url;
    }),
    replaceState: vi.fn((_data: unknown, _unused: string, url: string) => {
      path = url;
    }),
  };
  const navigator = createNavigator({
    history,
    getPathname: () => path,
    addPopStateListener: (listener) => {
      popStateListener = listener;
    },
  });
  // Simula Atrás o Adelante: el navegador ya cambió la dirección cuando emite popstate
  const goBackTo = (previous: string) => {
    path = previous;
    popStateListener?.();
  };
  return { history, navigator, goBackTo };
}

describe("createNavigator", () => {
  it("getPath devuelve la dirección actual del navegador", () => {
    const { navigator } = fakeBrowser("/map");
    expect(navigator.getPath()).toBe("/map");
  });

  it("navigate añade una entrada al historial y avisa a quien escucha", () => {
    const { history, navigator } = fakeBrowser("/map");
    const listener = vi.fn();
    navigator.subscribe(listener);

    navigator.navigate("/register");

    expect(history.pushState).toHaveBeenCalledExactlyOnceWith(null, "", "/register");
    expect(history.replaceState).not.toHaveBeenCalled();
    expect(navigator.getPath()).toBe("/register");
    expect(listener).toHaveBeenCalledTimes(1);
  });

  it("navigate a la dirección actual no toca el historial ni avisa", () => {
    const { history, navigator } = fakeBrowser("/map");
    const listener = vi.fn();
    navigator.subscribe(listener);

    navigator.navigate("/map");

    expect(history.pushState).not.toHaveBeenCalled();
    expect(history.replaceState).not.toHaveBeenCalled();
    expect(listener).not.toHaveBeenCalled();
  });

  it("replace sustituye la entrada actual, sin añadir otra, y avisa", () => {
    const { history, navigator } = fakeBrowser("/register");
    const listener = vi.fn();
    navigator.subscribe(listener);

    navigator.replace("/map");

    expect(history.replaceState).toHaveBeenCalledExactlyOnceWith(null, "", "/map");
    expect(history.pushState).not.toHaveBeenCalled();
    expect(navigator.getPath()).toBe("/map");
    expect(listener).toHaveBeenCalledTimes(1);
  });

  it("un popstate avisa a quien escucha sin tocar el historial", () => {
    const { history, navigator, goBackTo } = fakeBrowser("/register");
    const listener = vi.fn();
    navigator.subscribe(listener);

    goBackTo("/map");

    expect(listener).toHaveBeenCalledTimes(1);
    expect(navigator.getPath()).toBe("/map");
    expect(history.pushState).not.toHaveBeenCalled();
    expect(history.replaceState).not.toHaveBeenCalled();
  });

  it("avisa a todos los que escuchan", () => {
    const { navigator } = fakeBrowser("/map");
    const first = vi.fn();
    const second = vi.fn();
    navigator.subscribe(first);
    navigator.subscribe(second);

    navigator.navigate("/register");

    expect(first).toHaveBeenCalledTimes(1);
    expect(second).toHaveBeenCalledTimes(1);
  });

  it("quien se da de baja deja de recibir avisos", () => {
    const { navigator, goBackTo } = fakeBrowser("/map");
    const listener = vi.fn();
    const unsubscribe = navigator.subscribe(listener);

    unsubscribe();
    navigator.navigate("/register");
    navigator.replace("/map");
    goBackTo("/register");

    expect(listener).not.toHaveBeenCalled();
  });
});

describe("isPlainLeftClick", () => {
  const plain = { button: 0, metaKey: false, ctrlKey: false, shiftKey: false, altKey: false, defaultPrevented: false };

  it("un clic izquierdo sin modificadores es un clic simple", () => {
    expect(isPlainLeftClick(plain)).toBe(true);
  });

  it.each([
    ["el botón central", { button: 1 }],
    ["el botón derecho", { button: 2 }],
    ["Cmd", { metaKey: true }],
    ["Ctrl", { ctrlKey: true }],
    ["Mayúsculas", { shiftKey: true }],
    ["Alt", { altKey: true }],
    ["un evento ya cancelado", { defaultPrevented: true }],
  ])("con %s no lo es: el enlace sigue abriéndose como el navegador decida", (_label, change) => {
    expect(isPlainLeftClick({ ...plain, ...change })).toBe(false);
  });
});
