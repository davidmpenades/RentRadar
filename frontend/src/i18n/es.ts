export const es = {
  notFound: {
    title: "Página no encontrada",
    goToMap: "Ir al mapa",
  },
  panel: {
    label: "Bienes en esta zona",
    searching: "Buscando bienes…",
    countOne: "1 bien en esta zona",
    countMany: "{count} bienes en esta zona",
    incompleteOne: "Mostrando 1 bien. Puede haber más: acerca el mapa para verlos todos",
    incompleteMany: "Mostrando {count} bienes. Puede haber más: acerca el mapa para verlos todos",
    empty: "No hay bienes en esta zona",
    zoomIn: "Acerca el mapa para ver los bienes",
    resetView: "Volver a la zona inicial",
    radius: "Zona de unos {radius}",
    priceUnit: { hour: "hora", day: "día", week: "semana", month: "mes" },
    errors: {
      network: "No hay conexión. Comprueba tu red y vuelve a intentarlo.",
      timeout: "El servidor tarda demasiado en responder.",
      server: "Ha habido un problema en el servidor.",
      throttled: "Has hecho muchas búsquedas seguidas. Espera un momento y vuelve a intentarlo.",
      invalid: "No se han podido leer los bienes.",
      unexpected: "Ha ocurrido un error inesperado. Vuelve a intentarlo.",
    },
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
