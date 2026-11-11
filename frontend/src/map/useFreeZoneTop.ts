import { useEffect, type RefObject } from "react";

import { freeZoneTop } from "./freeZoneTop";

const MAP_CONTROLS = ".maplibregl-ctrl-top-right";

// Escribe en la zona dónde acaban el zoom y la atribución; va por style y no por estado de React para no repintar la página cuando cambia
export function useFreeZoneTop(zoneRef: RefObject<HTMLElement | null>) {
  useEffect(() => {
    const zone = zoneRef.current;
    if (!zone) return;
    let controls: Element | null = null;
    let published: number | null = null;

    const publish = () => {
      const freeTop = freeZoneTop(controls?.getBoundingClientRect().bottom ?? null, zone.getBoundingClientRect().top);
      if (freeTop === published) return;
      published = freeTop;
      zone.style.setProperty("--free-top", `${freeTop}px`);
    };

    const resizeObserver = new ResizeObserver(publish);
    // Los controles nacen y mueren con el mapa; mientras sea el mismo elemento, su tamaño lo sigue el ResizeObserver
    const findControls = () => {
      const found = zone.querySelector(MAP_CONTROLS);
      if (found === controls) return;
      if (controls) resizeObserver.unobserve(controls);
      if (found) resizeObserver.observe(found);
      controls = found;
      publish();
    };

    const mutationObserver = new MutationObserver(findControls);
    resizeObserver.observe(zone);
    mutationObserver.observe(zone, { childList: true, subtree: true });
    findControls();

    return () => {
      mutationObserver.disconnect();
      resizeObserver.disconnect();
      zone.style.removeProperty("--free-top");
    };
  }, [zoneRef]);
}
