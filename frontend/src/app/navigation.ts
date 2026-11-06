type HistoryLike = {
  pushState(data: unknown, unused: string, url: string): void;
  replaceState(data: unknown, unused: string, url: string): void;
};

type NavigatorOptions = {
  history: HistoryLike;
  getPathname: () => string;
  addPopStateListener: (listener: () => void) => void;
};

export type AppNavigator = {
  getPath(): string;
  navigate(path: string): void;
  replace(path: string): void;
  subscribe(listener: () => void): () => void;
};

type ClickLike = {
  button: number;
  metaKey: boolean;
  ctrlKey: boolean;
  shiftKey: boolean;
  altKey: boolean;
  defaultPrevented: boolean;
};

export function createNavigator({ history, getPathname, addPopStateListener }: NavigatorOptions): AppNavigator {
  const listeners = new Set<() => void>();
  const notify = () => {
    for (const listener of listeners) listener();
  };
  // pushState y replaceState no emiten popstate: se avisa a mano
  addPopStateListener(notify);

  return {
    getPath: getPathname,
    navigate(path) {
      if (path === getPathname()) return;
      history.pushState(null, "", path);
      notify();
    },
    replace(path) {
      history.replaceState(null, "", path);
      notify();
    },
    subscribe(listener) {
      listeners.add(listener);
      return () => {
        listeners.delete(listener);
      };
    },
  };
}

// Con un modificador o con otro botón, el enlace se abre como decida el navegador (otra pestaña, otra ventana)
export function isPlainLeftClick(event: ClickLike): boolean {
  return (
    event.button === 0 &&
    !event.metaKey &&
    !event.ctrlKey &&
    !event.shiftKey &&
    !event.altKey &&
    !event.defaultPrevented
  );
}
