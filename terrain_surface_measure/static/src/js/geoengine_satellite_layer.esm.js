/** @odoo-module **/

/* global ol */

import {patch} from "@web/core/utils/patch";
import {FieldGeoEngineEditMap} from "@base_geoengine/js/widgets/geoengine_edit_map/field_geoengine_edit_map.esm";
import {GeoengineRenderer} from "@base_geoengine/js/views/geoengine/geoengine_renderer/geoengine_renderer.esm";

const SATELLITE_TILE_URL =
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}";

function createSatelliteSource(url = SATELLITE_TILE_URL) {
    return new ol.source.XYZ({
        url,
        cacheSize: 512,
        maxZoom: 19,
        crossOrigin: "anonymous",
        transition: 0,
    });
}

function createSatelliteLayer({url = SATELLITE_TILE_URL, visible = false} = {}) {
    return new ol.layer.Tile({
        title: "Satellite",
        visible,
        type: "base",
        preload: 2,
        opacity: 1,
        source: createSatelliteSource(url),
    });
}

function makeMapSwitchControl({getMode, setMode}) {
    const element = document.createElement("div");
    element.className = "ol-control terrain-map-switch";
    Object.assign(element.style, {
        top: "12px",
        right: "12px",
        left: "auto",
        display: "flex",
        overflow: "hidden",
        padding: "2px",
        borderRadius: "6px",
        background: "rgba(255, 255, 255, 0.92)",
        boxShadow: "0 1px 6px rgba(0, 0, 0, 0.25)",
    });

    const buttons = {};
    for (const [mode, label] of [
        ["map", "Map"],
        ["satellite", "Satellite"],
    ]) {
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = label;
        button.title = label;
        Object.assign(button.style, {
            minWidth: "74px",
            height: "34px",
            margin: "0",
            border: "0",
            borderRadius: "4px",
            fontSize: "12px",
            fontWeight: "600",
            color: "#263238",
            background: "transparent",
            cursor: "pointer",
        });
        button.addEventListener("click", () => {
            setMode(mode);
            refresh();
        });
        buttons[mode] = button;
        element.appendChild(button);
    }

    const refresh = () => {
        const activeMode = getMode();
        for (const [mode, button] of Object.entries(buttons)) {
            const isActive = mode === activeMode;
            button.style.background = isActive ? "#1a73e8" : "transparent";
            button.style.color = isActive ? "#ffffff" : "#263238";
        }
    };
    refresh();

    return new ol.control.Control({element});
}

patch(GeoengineRenderer.prototype, {
    createBackgroundLayers(backgrounds) {
        const arcgisLayers = backgrounds.filter(
            (background) => background.raster_type === "arcgis_xyz"
        );
        const standardLayers = backgrounds.filter(
            (background) => background.raster_type !== "arcgis_xyz"
        );
        const layers = super.createBackgroundLayers(standardLayers).filter(Boolean);
        const satelliteLayers = arcgisLayers.map((background) => {
            const layer = createSatelliteLayer({
                url: background.url,
                visible: !background.overlay,
            });
            layer.setOpacity(background.opacity);
            return layer;
        });
        return layers.concat(satelliteLayers);
    },

    renderMap() {
        super.renderMap(...arguments);
        if (!this.map || this._satelliteWarmupAttached) {
            return;
        }
        this._satelliteWarmupAttached = true;
        this.addTerrainMapSwitchControl();
        let timeout;
        const warmup = () => {
            clearTimeout(timeout);
            timeout = setTimeout(() => this.warmupSatelliteTiles(), 700);
        };
        warmup();
        this.map.on("moveend", warmup);
    },

    addTerrainMapSwitchControl() {
        const baseGroup = this.map
            .getLayers()
            .getArray()
            .find((layer) => layer.get("title") === "Base maps");
        const baseLayers = baseGroup?.getLayers().getArray() || [];
        const osmLayer = baseLayers.find((layer) => layer.get("title") === "OpenStreetMap");
        const satelliteLayer = baseLayers.find(
            (layer) => layer.get("title") === "Satellite"
        );
        if (!osmLayer || !satelliteLayer) {
            return;
        }
        this.map.addControl(
            makeMapSwitchControl({
                getMode: () => (satelliteLayer.getVisible() ? "satellite" : "map"),
                setMode: (mode) => {
                    const useSatellite = mode === "satellite";
                    osmLayer.setVisible(!useSatellite);
                    satelliteLayer.setVisible(useSatellite);
                    this.warmupSatelliteTiles();
                },
            })
        );
    },

    warmupSatelliteTiles() {
        const satelliteLayer = this.map
            .getLayers()
            .getArray()
            .find((layer) => layer.get("title") === "Base maps")
            ?.getLayers()
            .getArray()
            .find((layer) => layer.get("title") === "Satellite");

        const source = satelliteLayer?.getSource();
        const view = this.map.getView();
        if (!source || !view || !this.map.getSize()) {
            return;
        }

        const tileGrid = source.getTileGrid();
        const projection = view.getProjection();
        const z = tileGrid.getZForResolution(view.getResolution());
        const extent = view.calculateExtent(this.map.getSize());
        const range = tileGrid.getTileRangeForExtentAndZ(extent, z);
        const tileUrlFunction = source.getTileUrlFunction();

        let loaded = 0;
        for (let x = range.minX; x <= range.maxX; x++) {
            for (let y = range.minY; y <= range.maxY; y++) {
                if (loaded >= 12) {
                    return;
                }
                const url = tileUrlFunction([z, x, y], 1, projection);
                if (url) {
                    const image = new Image();
                    image.decoding = "async";
                    image.src = url;
                    loaded++;
                }
            }
        }
    },
});

patch(FieldGeoEngineEditMap.prototype, {
    renderMap() {
        super.renderMap(...arguments);
        if (this.props.record.resModel !== "terrain.surface" || this._terrainMapSwitch) {
            return;
        }
        this._terrainMapSwitch = true;
        const osmLayer = this.map
            .getLayers()
            .getArray()
            .find((layer) => layer instanceof ol.layer.Tile);
        const satelliteLayer = createSatelliteLayer();
        this.map.getLayers().insertAt(1, satelliteLayer);
        this.map.addControl(
            makeMapSwitchControl({
                getMode: () => (satelliteLayer.getVisible() ? "satellite" : "map"),
                setMode: (mode) => {
                    const useSatellite = mode === "satellite";
                    osmLayer.setVisible(!useSatellite);
                    satelliteLayer.setVisible(useSatellite);
                },
            })
        );
    },
});
