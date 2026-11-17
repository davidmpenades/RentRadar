from typing import NamedTuple

DEMO_EMAIL = "demo@example.com"
# (latitud, longitud) de la vista inicial del mapa
INITIAL_CENTRE = (39.4699, -0.3763)


class DemoAsset(NamedTuple):
    title: str
    description: str
    category_slug: str
    price: str
    price_unit: str
    privacy_radius: int
    latitude: float
    longitude: float
    active: bool


# Ubicaciones exactas ficticias a menos de 2 km del centro; la primera y la
# duodécima, con radio 1000, caen en la misma celda y comparten ubicación pública
DEMO_ASSETS = (
    DemoAsset(
        "Bicicleta eléctrica urbana",
        "Bicicleta eléctrica con cesta y batería de 60 km de autonomía, "
        "ideal para recorrer la ciudad.",
        "ebike",
        "8.00",
        "day",
        1000,
        39.4579,
        -0.3803,
        True,
    ),
    DemoAsset(
        "Caravana familiar para cuatro personas",
        "Caravana con cama doble, literas, cocina y nevera, lista para salir "
        "de escapada el fin de semana.",
        "caravan",
        "55.00",
        "day",
        500,
        39.4741,
        -0.3688,
        True,
    ),
    DemoAsset(
        "Autocaravana perfilada de siete metros",
        "Autocaravana con baño completo, calefacción y toldo, apta para viajes "
        "largos con toda la familia.",
        "motorhome",
        "120.00",
        "day",
        2000,
        39.4602,
        -0.3911,
        True,
    ),
    DemoAsset(
        "Furgoneta para mudanzas pequeñas",
        "Furgoneta de carga con rampa y correas de sujeción, perfecta para "
        "trasladar muebles o cajas.",
        "van",
        "35.00",
        "day",
        500,
        39.4776,
        -0.3820,
        True,
    ),
    DemoAsset(
        "Piscina con zona de césped",
        "Piscina privada de ocho por cuatro metros con zona de sombra, duchas "
        "y césped para reuniones.",
        "pool",
        "25.00",
        "hour",
        1000,
        39.4655,
        -0.3659,
        True,
    ),
    DemoAsset(
        "Barbacoa de obra con mesa",
        "Barbacoa de obra con mesa para ocho comensales y fregadero, en una "
        "terraza cubierta.",
        "barbecue",
        "20.00",
        "hour",
        2000,
        39.4809,
        -0.3903,
        True,
    ),
    DemoAsset(
        "Pista de pádel cubierta",
        "Pista de pádel con iluminación y vestuarios, disponible por horas "
        "entre semana y fines de semana.",
        "sports-area",
        "18.00",
        "hour",
        500,
        39.4688,
        -0.3902,
        True,
    ),
    DemoAsset(
        "Velero de recreo de nueve metros",
        "Velero con tres camarotes y equipo de seguridad, se alquila con patrón "
        "para salidas de un día.",
        "boat",
        "260.00",
        "day",
        1000,
        39.4610,
        -0.3702,
        True,
    ),
    DemoAsset(
        "Kayak doble de travesía",
        "Kayak doble con chalecos, remos y bolsa estanca para recorrer la costa "
        "en una mañana.",
        "kayak",
        "22.00",
        "day",
        2000,
        39.4824,
        -0.3653,
        True,
    ),
    DemoAsset(
        "Canoa para tres personas",
        "Canoa estable de tres plazas con remos y chalecos, adecuada para "
        "principiantes y para familias.",
        "canoe",
        "15.00",
        "hour",
        500,
        39.4591,
        -0.3705,
        True,
    ),
    DemoAsset(
        "Equipo de sonido para fiestas",
        "Equipo de sonido con dos altavoces, mesa de mezclas y micrófono "
        "inalámbrico para celebraciones.",
        "other",
        "45.00",
        "day",
        1000,
        39.4745,
        -0.3849,
        True,
    ),
    DemoAsset(
        "Bicicleta eléctrica plegable",
        "Bicicleta eléctrica plegable de ocho kilos, cabe en el maletero y es "
        "muy cómoda para trayectos mixtos.",
        "ebike",
        "6.50",
        "day",
        1000,
        39.4581,
        -0.3801,
        True,
    ),
    DemoAsset(
        "Caravana pequeña para dos personas",
        "Caravana ligera con cama doble y cocina, se puede remolcar con un "
        "coche de tamaño medio.",
        "caravan",
        "180.00",
        "week",
        2000,
        39.4569,
        -0.3863,
        True,
    ),
    DemoAsset(
        "Autocaravana compacta con placa solar",
        "Autocaravana de seis metros con placa solar y ducha exterior, pensada "
        "para escapadas de varios días.",
        "motorhome",
        "650.00",
        "week",
        500,
        39.4718,
        -0.3632,
        True,
    ),
    DemoAsset(
        "Furgoneta de nueve plazas para grupos",
        "Furgoneta de nueve plazas con aire acondicionado, ideal para "
        "excursiones y desplazamientos de grupos.",
        "van",
        "70.00",
        "day",
        1000,
        39.4789,
        -0.3731,
        True,
    ),
    DemoAsset(
        "Piscina climatizada por horas",
        "Piscina cubierta y climatizada con dos calles, disponible para clases "
        "y entrenamientos por horas.",
        "pool",
        "40.00",
        "hour",
        2000,
        39.4709,
        -0.3763,
        True,
    ),
    DemoAsset(
        "Parrilla de gas portátil",
        "Parrilla de gas con tres fuegos y carro de transporte, se entrega con "
        "bombona y utensilios básicos.",
        "barbecue",
        "12.00",
        "day",
        500,
        39.4672,
        -0.3695,
        True,
    ),
    DemoAsset(
        "Campo de fútbol siete de césped artificial",
        "Campo de fútbol siete con césped artificial, porterías y focos, para "
        "partidos entre amigos o equipos.",
        "sports-area",
        "60.00",
        "hour",
        1000,
        39.4763,
        -0.3902,
        True,
    ),
    DemoAsset(
        "Lancha neumática con motor",
        "Lancha neumática de cinco metros con motor de 40 caballos, no requiere "
        "titulación para uso costero.",
        "boat",
        "95.00",
        "day",
        2000,
        39.4584,
        -0.3723,
        True,
    ),
    DemoAsset(
        "Kayak individual de mar",
        "Kayak individual ligero con timón y chaleco incluido, recomendado para "
        "quienes ya han remado antes.",
        "kayak",
        "9.00",
        "hour",
        500,
        39.4645,
        -0.3740,
        True,
    ),
    DemoAsset(
        "Canoa canadiense de fibra",
        "Canoa de fibra de dos plazas con asientos acolchados, perfecta para "
        "rutas tranquilas por el río.",
        "canoe",
        "110.00",
        "month",
        1000,
        39.4676,
        -0.3920,
        True,
    ),
    DemoAsset(
        "Carpa de eventos de tres por seis",
        "Carpa plegable de eventos con paredes laterales, resistente al viento "
        "y fácil de montar entre dos personas.",
        "other",
        "75.00",
        "day",
        500,
        39.4750,
        -0.3673,
        True,
    ),
    DemoAsset(
        "Bicicleta eléctrica de montaña",
        "Bicicleta eléctrica de montaña con suspensión completa y dos baterías, "
        "para rutas exigentes en la sierra.",
        "ebike",
        "28.00",
        "day",
        500,
        39.4660,
        -0.3830,
        True,
    ),
    DemoAsset(
        "Equipo de esquí de pista completo",
        "Esquís con fijaciones, botas y bastones en varias tallas de adulto, "
        "revisados y listos para la temporada.",
        "ski",
        "49.90",
        "day",
        1000,
        39.4605,
        -0.3760,
        True,
    ),
    DemoAsset(
        "Piscina infantil con toldo",
        "Piscina poco profunda con toldo y zona de juegos, pausada mientras se "
        "renueva el vallado del jardín.",
        "pool",
        "10.00",
        "hour",
        500,
        39.4735,
        -0.3725,
        False,
    ),
)
