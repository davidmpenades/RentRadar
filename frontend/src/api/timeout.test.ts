import { describe, expect, it, vi } from "vitest";

import { runWithTimeout } from "./timeout";

const TIMEOUT_MS = 7_000;

// Un solo temporizador: basta para ver si se arma, con qué espera, si se cancela y cuántas veces
function createTimer() {
  let callback: (() => void) | undefined;
  const timer = {
    armedWith: [] as number[],
    cleared: [] as number[],
    setTimer(cb: () => void, ms: number): number {
      callback = cb;
      timer.armedWith.push(ms);
      return timer.armedWith.length;
    },
    clearTimer(handle: number): void {
      timer.cleared.push(handle);
      callback = undefined;
    },
    fire(): void {
      callback?.();
    },
  };
  return timer;
}

class TimedOut extends Error {}

function setup(signal?: AbortSignal) {
  const timer = createTimer();
  const onTimeout = vi.fn(() => new TimedOut());
  const run = <T>(task: (inner: AbortSignal) => Promise<T>) =>
    runWithTimeout(
      { signal, timeoutMs: TIMEOUT_MS, setTimer: timer.setTimer, clearTimer: timer.clearTimer, onTimeout },
      task,
    );
  return { timer, onTimeout, run };
}

// Una tarea que respeta la señal interna: no termina hasta que se aborta
function hanging(inner: AbortSignal): Promise<never> {
  return new Promise((_resolve, reject) => {
    inner.addEventListener("abort", () => reject(inner.reason), { once: true });
  });
}

async function rejection(promise: Promise<unknown>): Promise<unknown> {
  try {
    await promise;
  } catch (error) {
    return error;
  }
  throw new Error("La promesa se esperaba rechazada");
}

describe("runWithTimeout: la señal externa", () => {
  it("con la señal ya abortada lanza su motivo sin armar el temporizador ni llamar a la tarea", async () => {
    const external = new AbortController();
    external.abort();
    const { timer, onTimeout, run } = setup(external.signal);
    const task = vi.fn(async () => "hecho");

    const error = await rejection(run(task));

    expect(error).toBe(external.signal.reason);
    expect((error as DOMException).name).toBe("AbortError");
    expect(task).not.toHaveBeenCalled();
    expect(timer.armedWith).toEqual([]);
    expect(timer.cleared).toEqual([]);
    expect(onTimeout).not.toHaveBeenCalled();
  });

  it("abortada durante la tarea, su motivo sale tal cual y no cuenta como tiempo vencido", async () => {
    const external = new AbortController();
    const { timer, onTimeout, run } = setup(external.signal);
    let innerSignal: AbortSignal | undefined;

    const pending = run((inner) => {
      innerSignal = inner;
      return hanging(inner);
    });
    const reason = new Error("motivo propio");
    external.abort(reason);

    expect(await rejection(pending)).toBe(reason);
    expect(innerSignal?.aborted).toBe(true);
    expect(innerSignal?.reason).toBe(reason);
    expect(onTimeout).not.toHaveBeenCalled();
    expect(timer.cleared).toEqual([1]);
  });

  it("abortada sin motivo propio, la tarea ve el AbortError de la señal externa", async () => {
    const external = new AbortController();
    const { run } = setup(external.signal);

    const pending = run(hanging);
    external.abort();

    const error = await rejection(pending);
    expect(error).toBe(external.signal.reason);
    expect((error as DOMException).name).toBe("AbortError");
  });

  it("al terminar retira el listener: un abort externo posterior no aborta nada", async () => {
    const external = new AbortController();
    const { run } = setup(external.signal);
    let innerSignal: AbortSignal | undefined;

    await run(async (inner) => {
      innerSignal = inner;
      return "hecho";
    });
    external.abort();

    expect(innerSignal?.aborted).toBe(false);
  });

  it("tras un fallo también retira el listener", async () => {
    const external = new AbortController();
    const { run } = setup(external.signal);
    let innerSignal: AbortSignal | undefined;

    await rejection(
      run(async (inner) => {
        innerSignal = inner;
        throw new RangeError("fallo");
      }),
    );
    external.abort();

    expect(innerSignal?.aborted).toBe(false);
  });
});

describe("runWithTimeout: sin señal externa", () => {
  it("solo actúa el temporizador: arma la espera pedida y devuelve el resultado", async () => {
    const { timer, onTimeout, run } = setup();
    let innerSignal: AbortSignal | undefined;

    const result = await run(async (inner) => {
      innerSignal = inner;
      return 42;
    });

    expect(result).toBe(42);
    expect(innerSignal).toBeInstanceOf(AbortSignal);
    expect(innerSignal?.aborted).toBe(false);
    expect(timer.armedWith).toEqual([TIMEOUT_MS]);
    expect(onTimeout).not.toHaveBeenCalled();
  });

  it("al vencer, aborta la señal interna y lanza el error de onTimeout", async () => {
    const { timer, onTimeout, run } = setup();
    let innerSignal: AbortSignal | undefined;

    const pending = run((inner) => {
      innerSignal = inner;
      return hanging(inner);
    });
    expect(innerSignal?.aborted).toBe(false);
    timer.fire();

    const error = await rejection(pending);
    expect(error).toBeInstanceOf(TimedOut);
    expect(onTimeout).toHaveBeenCalledTimes(1);
    expect(innerSignal?.aborted).toBe(true);
  });
});

describe("runWithTimeout: el tiempo máximo con señal externa", () => {
  it("al vencer lanza onTimeout y la señal externa queda intacta", async () => {
    const external = new AbortController();
    const { timer, onTimeout, run } = setup(external.signal);
    let innerSignal: AbortSignal | undefined;

    const pending = run((inner) => {
      innerSignal = inner;
      return hanging(inner);
    });
    timer.fire();

    expect(await rejection(pending)).toBeInstanceOf(TimedOut);
    expect(onTimeout).toHaveBeenCalledTimes(1);
    expect(innerSignal?.aborted).toBe(true);
    expect(external.signal.aborted).toBe(false);
  });

  it("si la tarea lanza otro error tras vencer, sigue siendo un tiempo vencido", async () => {
    const { timer, onTimeout, run } = setup();

    const pending = run(
      (inner) =>
        new Promise<never>((_resolve, reject) => {
          inner.addEventListener("abort", () => reject(new TypeError("Failed to fetch")), { once: true });
        }),
    );
    timer.fire();

    expect(await rejection(pending)).toBeInstanceOf(TimedOut);
    expect(onTimeout).toHaveBeenCalledTimes(1);
  });
});

describe("runWithTimeout: errores de la tarea", () => {
  it("el error de la tarea se propaga tal cual y no es un tiempo vencido", async () => {
    const { onTimeout, run } = setup();
    const failure = new RangeError("fallo propio");

    const error = await rejection(
      run(async () => {
        throw failure;
      }),
    );

    expect(error).toBe(failure);
    expect(onTimeout).not.toHaveBeenCalled();
  });
});

describe("runWithTimeout: limpieza del temporizador", () => {
  it("lo cancela una sola vez, con su propio manejador, tras un éxito", async () => {
    const { timer, run } = setup();
    await run(async () => "hecho");
    expect(timer.cleared).toEqual([1]);
  });

  it("lo cancela una sola vez tras un fallo", async () => {
    const { timer, run } = setup();
    await rejection(
      run(async () => {
        throw new Error("fallo");
      }),
    );
    expect(timer.cleared).toEqual([1]);
  });

  it("lo cancela una sola vez tras vencer", async () => {
    const { timer, run } = setup();
    const pending = run(hanging);
    timer.fire();
    await rejection(pending);
    expect(timer.cleared).toEqual([1]);
  });

  it("lo cancela una sola vez tras una cancelación externa", async () => {
    const external = new AbortController();
    const { timer, run } = setup(external.signal);
    const pending = run(hanging);
    external.abort();
    await rejection(pending);
    expect(timer.cleared).toEqual([1]);
  });

  it("no lo cancela hasta que la tarea termina, también si el cuerpo tarda en llegar", async () => {
    const { timer, run } = setup();
    let finish: (value: string) => void = () => undefined;
    const pending = run(
      () =>
        new Promise<string>((resolve) => {
          finish = resolve;
        }),
    );

    await Promise.resolve();
    expect(timer.cleared).toEqual([]);
    finish("hecho");
    await pending;
    expect(timer.cleared).toEqual([1]);
  });
});
