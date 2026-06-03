{
    "name": "Terrain Surface Measure",
    "version": "18.0.1.0.0",
    "category": "GeoBI",
    "summary": "Test manual terrain border drawing and surface measurement",
    "author": "Local",
    "license": "AGPL-3",
    "depends": ["base_geoengine"],
    "data": [
        "security/ir.model.access.csv",
        "views/terrain_surface_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "terrain_surface_measure/static/src/js/geoengine_satellite_layer.esm.js",
        ],
    },
    "installable": True,
    "application": True,
}
