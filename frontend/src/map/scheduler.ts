export const REQUEST_DELAY_MS = 300;

export type ScheduledRequest = {
  signal: AbortSignal;
  // Falso en cuanto llega una petición más nueva o se cancela: la respuesta ya no debe pintarse
  isCurrent: () => boolean;
};

type SchedulerOptions<Handle> = {
  delayMs: number;
  setTimer: (callback: () => void, ms: number) => Handle;
  clearTimer: (handle: Handle) => void;
  run: (request: ScheduledRequest) => void;
};

export function createRequestScheduler<Handle>(options: SchedulerOptions<Handle>) {
  const { delayMs, setTimer, clearTimer, run } = options;
  // Envuelto en un objeto: un manejador de temporizador válido podría valer 0
  let pending: { handle: Handle } | undefined;
  let controller: AbortController | undefined;
  let sequence = 0;

  function clearPending(): void {
    if (!pending) return;
    clearTimer(pending.handle);
    pending = undefined;
  }

  // Siempre aborta la anterior y sube la secuencia; no compara con la petición previa
  function start(): void {
    controller?.abort();
    controller = new AbortController();
    sequence += 1;
    const mine = sequence;
    run({ signal: controller.signal, isCurrent: () => mine === sequence });
  }

  return {
    schedule(): void {
      clearPending();
      const handle = setTimer(() => {
        pending = undefined;
        start();
      }, delayMs);
      pending = { handle };
    },
    runNow(): void {
      clearPending();
      start();
    },
    // Idempotente: StrictMode monta, desmonta y vuelve a montar
    cancel(): void {
      clearPending();
      controller?.abort();
      controller = undefined;
      sequence += 1;
    },
  };
}
