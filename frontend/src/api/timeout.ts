type TimeoutOptions<Handle> = {
  signal?: AbortSignal;
  timeoutMs: number;
  setTimer: (callback: () => void, ms: number) => Handle;
  clearTimer: (handle: Handle) => void;
  onTimeout: () => Error;
};

// La tarea incluye leer y validar el cuerpo: así el tiempo máximo cubre también un cuerpo que no llega
export async function runWithTimeout<Handle, T>(
  options: TimeoutOptions<Handle>,
  task: (signal: AbortSignal) => Promise<T>,
): Promise<T> {
  const { signal, timeoutMs, setTimer, clearTimer, onTimeout } = options;
  signal?.throwIfAborted();

  // Controlador propio para enlazar a mano la señal externa y el tiempo máximo
  const controller = new AbortController();
  let timedOut = false;
  const abortWithExternal = () => controller.abort(signal?.reason);
  signal?.addEventListener("abort", abortWithExternal, { once: true });
  const timer = setTimer(() => {
    timedOut = true;
    controller.abort();
  }, timeoutMs);

  try {
    return await task(controller.signal);
  } catch (error) {
    if (timedOut) throw onTimeout();
    // Si abortó la señal externa, el AbortError sale tal cual y quien pidió lo descarta
    throw error;
  } finally {
    clearTimer(timer);
    signal?.removeEventListener("abort", abortWithExternal);
  }
}
