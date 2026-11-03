import { describe, expect, it } from "vitest";

import { createRequestScheduler, REQUEST_DELAY_MS, type ScheduledRequest } from "./scheduler";

// Reloj a mano: los temporizadores pendientes se ven y solo vencen con advance
function createFakeClock() {
  let now = 0;
  let nextHandle = 1;
  const timers = new Map<number, { dueAt: number; callback: () => void }>();
  return {
    setTimer(callback: () => void, ms: number): number {
      const handle = nextHandle++;
      timers.set(handle, { dueAt: now + ms, callback });
      return handle;
    },
    clearTimer(handle: number): void {
      timers.delete(handle);
    },
    advance(ms: number): void {
      const target = now + ms;
      for (;;) {
        const due = [...timers.entries()]
          .filter(([, timer]) => timer.dueAt <= target)
          .sort(([, a], [, b]) => a.dueAt - b.dueAt)[0];
        if (!due) break;
        const [handle, timer] = due;
        timers.delete(handle);
        now = timer.dueAt;
        timer.callback();
      }
      now = target;
    },
    get pending(): number {
      return timers.size;
    },
  };
}

function setup() {
  const clock = createFakeClock();
  const requests: ScheduledRequest[] = [];
  const scheduler = createRequestScheduler({
    delayMs: 300,
    setTimer: clock.setTimer,
    clearTimer: clock.clearTimer,
    run: (request) => {
      requests.push(request);
    },
  });
  return { clock, requests, scheduler };
}

describe("createRequestScheduler: espera", () => {
  it("la espera por defecto de la interfaz es de 300 ms", () => {
    expect(REQUEST_DELAY_MS).toBe(300);
  });

  it("lanza la petición a los 300 ms y no antes", () => {
    const { clock, requests, scheduler } = setup();
    scheduler.schedule();
    clock.advance(299);
    expect(requests).toHaveLength(0);
    clock.advance(1);
    expect(requests).toHaveLength(1);
    expect(clock.pending).toBe(0);
  });

  it("cada movimiento reinicia la espera y solo pide la última", () => {
    const { clock, requests, scheduler } = setup();
    scheduler.schedule();
    clock.advance(200);
    scheduler.schedule();
    clock.advance(200);
    scheduler.schedule();
    expect(clock.pending).toBe(1);
    clock.advance(299);
    expect(requests).toHaveLength(0);
    clock.advance(1);
    expect(requests).toHaveLength(1);
    clock.advance(10_000);
    expect(requests).toHaveLength(1);
  });

  it("runNow pide en el acto y anula la espera pendiente", () => {
    const { clock, requests, scheduler } = setup();
    scheduler.schedule();
    scheduler.runNow();
    expect(requests).toHaveLength(1);
    expect(clock.pending).toBe(0);
    clock.advance(10_000);
    expect(requests).toHaveLength(1);
  });

  it("no deduplica: dos peticiones seguidas lanzan dos", () => {
    const { requests, scheduler } = setup();
    scheduler.runNow();
    scheduler.runNow();
    expect(requests).toHaveLength(2);
  });
});

describe("createRequestScheduler: petición anterior", () => {
  it("la nueva petición aborta la anterior y la deja obsoleta", () => {
    const { requests, scheduler } = setup();
    scheduler.runNow();
    scheduler.runNow();
    const [first, second] = requests;
    expect(first?.signal.aborted).toBe(true);
    expect(first?.isCurrent()).toBe(false);
    expect(second?.signal.aborted).toBe(false);
    expect(second?.isCurrent()).toBe(true);
  });

  it("la anterior sigue viva mientras dura la espera y se aborta al vencer", () => {
    const { clock, requests, scheduler } = setup();
    scheduler.runNow();
    scheduler.schedule();
    clock.advance(299);
    expect(requests[0]?.signal.aborted).toBe(false);
    expect(requests[0]?.isCurrent()).toBe(true);
    clock.advance(1);
    expect(requests[0]?.signal.aborted).toBe(true);
    expect(requests[0]?.isCurrent()).toBe(false);
    expect(requests[1]?.isCurrent()).toBe(true);
  });

  it("una respuesta vieja se descarta aunque llegue después de la nueva", async () => {
    const painted: string[] = [];
    const clock = createFakeClock();
    const resolvers: ((value: string) => void)[] = [];
    const settled: Promise<void>[] = [];
    const scheduler = createRequestScheduler({
      delayMs: 300,
      setTimer: clock.setTimer,
      clearTimer: clock.clearTimer,
      run: ({ isCurrent }) => {
        settled.push(
          new Promise<string>((resolve) => resolvers.push(resolve)).then((value) => {
            if (isCurrent()) painted.push(value);
          }),
        );
      },
    });
    scheduler.runNow();
    scheduler.runNow();
    resolvers[1]?.("nueva");
    resolvers[0]?.("vieja");
    await Promise.all(settled);
    expect(settled).toHaveLength(2);
    expect(painted).toEqual(["nueva"]);
  });
});

describe("createRequestScheduler: cancel", () => {
  it("anula la espera pendiente", () => {
    const { clock, requests, scheduler } = setup();
    scheduler.schedule();
    scheduler.cancel();
    expect(clock.pending).toBe(0);
    clock.advance(10_000);
    expect(requests).toHaveLength(0);
  });

  it("aborta la petición en vuelo y descarta su respuesta (pasar a no pedir)", () => {
    const { requests, scheduler } = setup();
    scheduler.runNow();
    scheduler.cancel();
    expect(requests[0]?.signal.aborted).toBe(true);
    expect(requests[0]?.isCurrent()).toBe(false);
  });

  it("es idempotente: se puede llamar sin nada en marcha y varias veces", () => {
    const { clock, requests, scheduler } = setup();
    expect(() => {
      scheduler.cancel();
      scheduler.cancel();
    }).not.toThrow();
    scheduler.runNow();
    scheduler.cancel();
    expect(() => scheduler.cancel()).not.toThrow();
    expect(clock.pending).toBe(0);
    expect(requests).toHaveLength(1);
  });

  it("tras cancelar se puede volver a pedir (montaje doble de StrictMode)", () => {
    const { clock, requests, scheduler } = setup();
    scheduler.cancel();
    scheduler.runNow();
    scheduler.cancel();
    scheduler.runNow();
    scheduler.schedule();
    clock.advance(300);
    expect(requests).toHaveLength(3);
    expect(requests[2]?.isCurrent()).toBe(true);
    expect(requests[1]?.isCurrent()).toBe(false);
  });
});
