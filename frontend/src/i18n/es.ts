export const es = {
  notFound: {
    title: "Página no encontrada",
    goToMap: "Ir al mapa",
  },
  map: {
    notice:
      "Ubicación aproximada: cada bien está en algún punto dentro de su círculo, de 500 m a 2 km de radio según el anuncio. Nunca se muestra la dirección.",
    styleError: "No se ha podido cargar el mapa.",
    retry: "Reintentar",
    // Textos de los controles de MapLibre, con las claves que él define
    locale: {
      "Map.Title": "Mapa de bienes en alquiler",
      "NavigationControl.ZoomIn": "Acercar",
      "NavigationControl.ZoomOut": "Alejar",
      "AttributionControl.ToggleAttribution": "Mostrar u ocultar la atribución",
      "AttributionControl.MapFeedback": "Comentarios sobre el mapa",
    },
  },
} as const;
