import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams } from 'react-router';
import type { Map as MlMap } from 'maplibre-gl';
import { api } from '../api/client';
import { useStatus } from '../api/status';
import type { NearbyFacility, NearbyPlace, Place } from '../api/types';
import { errorMessage, useQuery } from '../api/useQuery';
import { notify } from '../components/Notice';
import { QrCode } from '../components/QrCode';
import { Icon } from '../icons';
import { useTheme } from '../theme/ThemeProvider';
import { gridRef } from '../map/grid';
import { floodZoneAt } from '../map/home';
import { LayerChips, type Terrain } from '../map/LayerChips';
import { MapPanel, type PanelBodySize } from '../map/MapPanel';
import { MapView } from '../map/MapView';
import { bearingDeg, formatBearing, formatDistance, pathLengthKm, type LngLat } from '../map/measure';
import { describeNearby, describeRoute, leadFacility, NEARBY_KIND, nearbyGap, nearbyIcon, placeName, plainNote } from '../map/nearby';
import { PlaceCard, type From } from '../map/PlaceCard';
import { PlaceSearch } from '../map/PlaceSearch';
import type { TappedPlace } from '../map/tooltip';
import { mapQueryString, parseMapQuery } from '../map/query';
import { PrintButton } from '../components/PrintButton';
import { Screen } from '../shell/Screen';
import './map.css';

type Panel = 'none' | 'search' | 'pins' | 'share' | 'home' | 'nearby' | 'place';
const DEFAULT_VIEW = { lat: 54.5, lon: -3.5, zoom: 5.5 };

export function MapScreen() {
  const { theme } = useTheme();
  const { status } = useStatus();
  const [params, setParams] = useSearchParams();
  const query = useMemo(() => parseMapQuery(`?${params.toString()}`), [params]);
  const { data: config, error, loading } = useQuery(() => api.mapConfig(), []);
  const pinsQ = useQuery(() => api.notes('pin'), [], { refetchOnFocus: true });
  // What to expect at each kind of place, once per screen: the card reads its own kind out of it.
  const placesQ = useQuery(() => api.mapPlaces(), []);
  const homeQ = useQuery(() => api.home(), [], { refetchOnFocus: true });
  const mapRef = useRef<MlMap | null>(null);

  // The default set of overlays depends on config (async) plus the initial ?overlay= query, so it can only be
  // computed once config has loaded; overlayOverride holds the user's own toggles from then on. Deriving this
  // with useMemo (rather than a useEffect + setState) lets the map render in the same commit config arrives in.
  const [overlayOverride, setOverlayOverride] = useState<string[] | null>(null);
  const overlaysOn = useMemo(() => {
    if (overlayOverride) return overlayOverride;
    if (!config) return null;
    const wanted = query.overlays.length ? query.overlays : config.overlays.filter((o) => o.default_on).map((o) => o.id);
    return wanted.filter((id) => config.overlays.some((o) => o.id === id && o.available));
  }, [overlayOverride, config, query.overlays]);
  const [terrain, setTerrain] = useState<Terrain>({ contours: true, hillshade: true });
  const [panel, setPanel] = useState<Panel>('none');
  const [view, setView] = useState({ lat: query.lat ?? DEFAULT_VIEW.lat, lon: query.lon ?? DEFAULT_VIEW.lon, zoom: query.z ?? DEFAULT_VIEW.zoom });
  const [tapped, setTapped] = useState<LngLat | null>(null);
  // The place the last tap landed on, and the card that says what it is.
  const [place, setPlace] = useState<TappedPlace | null>(null);
  const [measuring, setMeasuring] = useState(false);
  const [measure, setMeasure] = useState<LngLat[]>([]);
  const [pendingPin, setPendingPin] = useState<LngLat | null>(null);
  const [pinTitle, setPinTitle] = useState('');
  const [printImage, setPrintImage] = useState<string | null>(null);
  const [homeLabel, setHomeLabel] = useState('Home');
  const [savingHome, setSavingHome] = useState(false);
  // The facilities list is for one point, captured when the panel opens, so it does not chase the map.
  const [nearbyAt, setNearbyAt] = useState<LngLat | null>(null);
  // And that point is the household's own home whenever the box has one. The panel used to search
  // from wherever the map happened to be — which, with no home in the query string, was the middle
  // of the country — and told a household its nearest A&E was an hour's walk when it was three
  // minutes away. Nothing on the panel said which point it had searched from.
  const [nearbyOrigin, setNearbyOrigin] = useState<'home' | 'centre' | 'place'>('home');
  // What the panel calls the point it searched from when that point is a place off the card.
  const [nearbyLabel, setNearbyLabel] = useState('');
  const nearbyQ = useQuery(() => (nearbyAt ? api.nearby(nearbyAt.lat, nearbyAt.lon) : Promise.resolve(null)), [nearbyAt]);
  // Which kind of place the panel is answering for. It survives a fresh search from a new centre, so
  // somebody looking for a pharmacy is still shown a pharmacy after they move the map.
  const [nearbyKind, setNearbyKind] = useState<string | null>(null);
  // The share code is sized to the panel it sits in rather than to a number, so it is never the
  // picture whose bottom third is under the edge of a phone sheet.
  const [shareBody, setShareBody] = useState<PanelBodySize | null>(null);
  const [routeTo, setRouteTo] = useState<{ title: string; lat: number; lon: number } | null>(null);
  const labelPoint = useMemo(() => (query.label && query.lat !== null && query.lon !== null ? { lat: query.lat, lon: query.lon, label: query.label } : null), [query]);

  useEffect(() => {
    if (!overlaysOn) return;
    const next = mapQueryString({ lat: view.lat, lon: view.lon, z: view.zoom, overlays: overlaysOn, label: query.label });
    if (next !== `?${params.toString()}`) setParams(new URLSearchParams(next), { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view, overlaysOn]);


  const flyTo = useCallback((lon: number, lat: number, zoom = 13) => mapRef.current?.flyTo({ center: [lon, lat], zoom }), []);
  const onPick = (p: Place) => { flyTo(p.lon, p.lat, p.kind === 'Postcode' ? 15 : 13); setPanel('none'); };
  const onGrid = (point: { lat: number; lon: number }) => { flyTo(point.lon, point.lat, 15); setPanel('none'); };
  const onMapClick = (p: LngLat) => { if (measuring) setMeasure((m) => [...m, p]); else setTapped(p); };

  /* The map opens where the household lives. With no point in the address it used to open on the
     default extent — NY 0295 1266 at a 100 km scale, the Cumbrian coast, some 500 km from the home
     the box has stored — and everything measured from the middle of the screen measured from there.
     A link that names a point still wins; this only fills the gap a bare /map leaves. */
  const homedRef = useRef(false);
  useEffect(() => {
    if (homedRef.current || query.lat !== null || query.lon !== null) return;
    const at = homeQ.data;
    if (!at || at.lat === null || at.lon === null) return;
    homedRef.current = true;
    setView({ lat: at.lat, lon: at.lon, zoom: 14 });
    flyTo(at.lon, at.lat, 14);
  }, [homeQ.data, query.lat, query.lon, flyTo]);

  /* With no home and no point in the address, ask the device once where it is (browsers only allow
     that over HTTPS or on localhost, which `canLocate` already knows). A refusal or a timeout is
     silent: the country view is the fallback, and Find place still offers Locate me. */
  const canLocate = typeof window !== 'undefined' && window.isSecureContext && Boolean(navigator.geolocation);
  const locatedRef = useRef(false);
  useEffect(() => {
    if (locatedRef.current || homedRef.current || query.lat !== null || query.lon !== null) return;
    if (homeQ.loading) return;                       // a home may still be on its way
    const at = homeQ.data;
    if ((at && (at.lat !== null || at.lon !== null)) || !canLocate) return;
    locatedRef.current = true;
    navigator.geolocation.getCurrentPosition(
      (pos) => { setView({ lat: pos.coords.latitude, lon: pos.coords.longitude, zoom: 14 }); flyTo(pos.coords.longitude, pos.coords.latitude, 14); },
      () => undefined,
      { timeout: 10_000 },
    );
  }, [homeQ.data, homeQ.loading, query.lat, query.lon, flyTo, canLocate]);

  const savePin = async () => {
    const at = pendingPin ?? { lat: view.lat, lon: view.lon };
    try {
      await api.createNote({ kind: 'pin', title: pinTitle.trim() || 'Pin', body: '', lat: at.lat, lon: at.lon });
      setPendingPin(null);
      setPinTitle('');
      await pinsQ.refetch();
    } catch (e) {
      notify(`Could not save the pin: ${errorMessage(e)}`);
    }
  };
  const deletePin = async (id: number) => {
    try {
      await api.deleteNote(id);
      await pinsQ.refetch();
    } catch (e) {
      notify(`Could not delete the pin: ${errorMessage(e)}`);
    }
  };

  const home = homeQ.data ?? null;
  const homePoint = home && home.lat !== null && home.lon !== null ? { lat: home.lat, lon: home.lon, label: home.label || 'Home' } : null;
  // A route runs from home when there is one, and from the centre of the screen when there is not.
  const routeFrom = homePoint ?? { lat: view.lat, lon: view.lon, label: 'the centre' };
  const route = routeTo ? describeRoute(routeFrom, { lat: routeTo.lat, lon: routeTo.lon }, routeTo.title, homePoint ? 'home' : 'the centre') : null;
  const routePoints: LngLat[] = routeTo ? [{ lat: routeFrom.lat, lon: routeFrom.lon }, { lat: routeTo.lat, lon: routeTo.lon }] : [];

  const saveHome = async () => {
    const at = { lat: view.lat, lon: view.lon };
    const map = mapRef.current;
    // The flood zone is read from the overlay as drawn; with the overlay off the box records nothing
    // rather than guessing, and the panel says so.
    let flood: string | null = null;
    try {
      if (map) flood = floodZoneAt(map, map.project([at.lon, at.lat]));
    } catch {
      flood = null; // no flood overlay in this style
    }
    setSavingHome(true);
    try {
      const saved = await api.setHome({ lat: at.lat, lon: at.lon, label: homeLabel.trim() || 'Home', flood_zone: flood });
      homeQ.setData(saved);
      notify(`Home set${saved.flood_zone ? `, flood zone ${saved.flood_zone}` : ''}.`);
    } catch (e) {
      notify(`Could not set home: ${errorMessage(e)}`);
    } finally {
      setSavingHome(false);
    }
  };

  const openNearby = () => {
    setPanel('nearby');
    setNearbyOrigin(homePoint ? 'home' : 'centre');
    setNearbyAt(homePoint ? { lat: homePoint.lat, lon: homePoint.lon } : { lat: view.lat, lon: view.lon });
  };
  const searchFrom = (where: 'home' | 'centre') => {
    setNearbyOrigin(where);
    const at = where === 'home' && homePoint ? { lat: homePoint.lat, lon: homePoint.lon } : { lat: view.lat, lon: view.lon };
    setNearbyAt(at);
  };

  /* A row in the Nearby list is a place like any other on the map: it opens the same card, with the
     same guidance on it, rather than only flying the map to a dot the household then has to find. A
     facility the box has no guidance for (a fire station, a rest centre) has nothing to put on that card
     but the name already in the list, so those rows only fly the map, as every row used to. */
  const openFromNearby = (f: NearbyFacility, p: NearbyPlace) => {
    flyTo(p.lon, p.lat, 15);
    const kind = NEARBY_KIND[f.id];
    if (!kind) return;
    setPlace({
      title: placeName(p.name, f.title), typeLine: f.title, overlay: f.title, overlayId: f.id,
      kind, rows: [], lat: p.lat, lon: p.lon,
    });
    setPanel('place');
  };

  /** The box asks the device where it is where it can, and says why it cannot where it cannot.
   * Either way the answer lives in the Find place panel, so there is one place to look. */
  const locate = () => {
    navigator.geolocation.getCurrentPosition(
      (pos) => { flyTo(pos.coords.longitude, pos.coords.latitude, 14); setPanel('none'); },
      () => notify('No position available on this device.'),
      { timeout: 10_000 },
    );
  };

  const toolbarRef = useRef<HTMLDivElement>(null);
  const scrollTools = () => toolbarRef.current?.scrollBy({ left: 200, behavior: 'smooth' });
  // The strip says when there is more of it than fits, rather than clipping a tool's name in half:
  // the fade and the chevron appear only when it actually scrolls, at any width.
  const [toolsScroll, setToolsScroll] = useState(false);
  useEffect(() => {
    const el = toolbarRef.current;
    if (!el) return;
    const check = () => setToolsScroll(el.scrollWidth > el.clientWidth + 1);
    check();
    window.addEventListener('resize', check);
    const observer = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(check);
    observer?.observe(el);
    return () => {
      window.removeEventListener('resize', check);
      observer?.disconnect();
    };
  }, [status, config]);

  const copyLink = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl);
      notify('The link is on the clipboard.');
    } catch {
      notify('This browser will not copy for us. Press and hold the link to copy it.');
    }
  };

  const print = () => {
    const map = mapRef.current;
    if (!map) return;
    setPrintImage(map.getCanvas().toDataURL('image/png'));
  };

  const centreRef = gridRef(view.lat, view.lon);
  const tappedRef = tapped ? gridRef(tapped.lat, tapped.lon) : null;
  const measureText = measure.length >= 2
    ? `${formatDistance(pathLengthKm(measure))}, bearing ${formatBearing(bearingDeg(measure[measure.length - 2], measure[measure.length - 1]))}`
    : measuring ? 'Tap two or more points' : null;
  const shareUrl = `http://${status?.hotspot.ip ?? window.location.host}/map${mapQueryString({ lat: view.lat, lon: view.lon, z: view.zoom, overlays: overlaysOn ?? [], label: query.label })}`;
  const legend = (config?.overlays ?? []).filter((o) => overlaysOn?.includes(o.id));

  // Every distance on the card is measured from the same point the rest of the screen measures from.
  const from: From = homePoint ? { lat: homePoint.lat, lon: homePoint.lon, label: 'home' } : { lat: view.lat, lon: view.lon, label: 'the map centre' };
  const fromHome = nearbyOrigin === 'home' && Boolean(homePoint) && Boolean(nearbyAt);
  const nearbyFromLabel = nearbyOrigin === 'place' ? nearbyLabel : fromHome ? 'home' : 'the map centre';
  const nearbyFacilities = nearbyQ.data?.facilities ?? [];
  const nearbyLead = leadFacility(nearbyFacilities, nearbyKind);
  const nearbyNearest = nearbyLead?.nearest ?? null;
  // The code takes whatever the body can show whole: its width, and its height less the address, the
  // line under it and the caption. Under about 130 px no camera reads a link this long, so that is
  // the floor and the body scrolls the last few pixels instead.
  const shareQrSize = shareBody ? Math.max(132, Math.min(220, shareBody.width - 8, shareBody.height - 116)) : 220;

  return (
    <Screen title="Map" search={false} back={false} fill className="map-screen">
      {/* Print was a non-scrolling row of its own above the tools; it is the eighth tool, and the
          strip fades and offers a chevron at its right edge rather than clipping "Ho" mid-word. */}
      <div className={toolsScroll ? 'map-toolbar map-toolbar-scrolls no-print' : 'map-toolbar no-print'}>
      <div className="map-tools" role="toolbar" aria-label="Map tools" ref={toolbarRef}>
        <button type="button" className={panel === 'search' ? 'btn btn-small active' : 'btn btn-small'} aria-pressed={panel === 'search'} onClick={() => setPanel(panel === 'search' ? 'none' : 'search')}><Icon name="search" size={18} /><span>Find place</span></button>
        <button type="button" className={panel === 'pins' ? 'btn btn-small active' : 'btn btn-small'} aria-pressed={panel === 'pins'} onClick={() => setPanel(panel === 'pins' ? 'none' : 'pins')}><Icon name="pin" size={18} /><span>Pins</span></button>
        <button type="button" className={panel === 'home' ? 'btn btn-small active' : 'btn btn-small'} aria-pressed={panel === 'home'} onClick={() => setPanel(panel === 'home' ? 'none' : 'home')}><Icon name="home" size={18} /><span>Home</span></button>
        <button type="button" className={panel === 'nearby' ? 'btn btn-small active' : 'btn btn-small'} aria-pressed={panel === 'nearby'} onClick={() => (panel === 'nearby' ? setPanel('none') : openNearby())}><Icon name="locate" size={18} /><span>Nearby</span></button>
        <button type="button" className={measuring ? 'btn btn-small active' : 'btn btn-small'} aria-pressed={measuring} onClick={() => { setMeasuring(!measuring); if (measuring) setMeasure([]); }}><Icon name="measure" size={18} /><span>Measure</span></button>
        <button type="button" className={panel === 'share' ? 'btn btn-small active' : 'btn btn-small'} aria-pressed={panel === 'share'} onClick={() => setPanel(panel === 'share' ? 'none' : 'share')}><Icon name="share" size={18} /><span>Share</span></button>
        <PrintButton onPrint={print} />
      </div>
      {/* An icon always has a word, and this one had none: a bare chevron beside "Sha" cut off
          mid-word is not a tool a household can find Print behind. */}
      {toolsScroll && <button type="button" className="btn btn-small map-tools-more" onClick={scrollTools}><span>More tools</span><Icon name="forward" size={18} /></button>}
      </div>
      {/* The layers are the map: they sit under the tools where a household can see what is on,
          not behind a button and a panel that covered the ground they were drawn on. */}
      {config && overlaysOn && (
        <LayerChips
          config={config} overlaysOn={overlaysOn}
          onToggle={(id, on) => setOverlayOverride(on ? [...overlaysOn, id] : overlaysOn.filter((x) => x !== id))}
          terrain={terrain} onTerrain={setTerrain}
        />
      )}
      <div className="map-host">
        {loading && <p className="map-note muted">Loading map…</p>}
        {error && <p className="map-note warning">Map unavailable: {error}</p>}
        {config && overlaysOn && (
          <MapView
            config={config} theme={theme} overlaysOn={overlaysOn} terrain={terrain}
            center={[view.lon, view.lat]} zoom={view.zoom} pins={pinsQ.data ?? []} labelPoint={labelPoint} measurePoints={measure}
            home={homePoint} routePoints={routePoints}
            onMoveEnd={setView} onClick={onMapClick}
            onFeatureTap={(p) => { if (measuring) return; setPlace(p); setPanel(p ? 'place' : panel === 'place' ? 'none' : panel); }}
            onLongPress={(p) => { setPendingPin(p); setPanel('pins'); }} onReady={(m) => { mapRef.current = m; }}
          />
        )}
        {/* The map's own three controls, in the app's shape: an icon and a word, 48 px, in the
            theme, and a compass that says what pressing it does. */}
        {config && overlaysOn && (
          <div className="map-nav no-print" role="group" aria-label="Move the map">
            <button type="button" className="btn btn-small" onClick={() => mapRef.current?.zoomIn()}><Icon name="plus" size={18} /><span>Zoom in</span></button>
            <button type="button" className="btn btn-small" onClick={() => mapRef.current?.zoomOut()}><Icon name="minus" size={18} /><span>Zoom out</span></button>
            <button type="button" className="btn btn-small" onClick={() => mapRef.current?.resetNorth()}><Icon name="compass" size={18} /><span>Face north</span></button>
          </div>
        )}
        {labelPoint && <div className="map-label">{labelPoint.label}</div>}
        {panel === 'search' && (
          <MapPanel label="Find place" title="Find a place" onClose={() => setPanel('none')}>
            {canLocate ? (
              <button type="button" className="btn" onClick={locate}><Icon name="locate" size={18} /><span>Locate me</span></button>
            ) : (
              <p className="warning">GPS is blocked over HTTP on phones, so the box cannot read your position. Type a place, a postcode or a grid reference instead.</p>
            )}
            <PlaceSearch onPick={onPick} onGrid={onGrid} />
            {!canLocate && config?.packs_index_url && <p>For GPS on your phone, install the offline <a href={config.packs_index_url}>Phone map packs</a>.</p>}
          </MapPanel>
        )}
        {panel === 'pins' && (
          <MapPanel label="Pins" title="Pins" onClose={() => setPanel('none')}>
            {pendingPin || pinTitle ? (
              <form className="stack" onSubmit={(e) => { e.preventDefault(); void savePin(); }}>
                <label className="field"><span>Pin name</span><input type="text" aria-label="Pin name" value={pinTitle} onChange={(e) => setPinTitle(e.target.value)} maxLength={80} /></label>
                <p className="muted">{gridRef((pendingPin ?? view).lat, (pendingPin ?? view).lon).text}</p>
                <div className="row"><button type="submit" className="btn btn-primary">Save pin</button><button type="button" className="btn" onClick={() => { setPendingPin(null); setPinTitle(''); }}>Cancel</button></div>
              </form>
            ) : (
              <button type="button" className="btn btn-primary" onClick={() => setPendingPin({ lat: view.lat, lon: view.lon })}>Drop a pin at the centre</button>
            )}
            <p className="muted">Long-press the map to drop a pin there.</p>
            <ul className="list">
              {(pinsQ.data ?? []).map((p) => (
                <li key={p.id} className="row">
                  <button type="button" className="btn" onClick={() => p.lat !== null && p.lon !== null && flyTo(p.lon, p.lat, 15)}>{p.title}</button>
                  <span className="muted">{p.lat !== null && p.lon !== null ? gridRef(p.lat, p.lon, 6).text : ''}</span>
                  <button type="button" className="btn btn-danger" onClick={() => void deletePin(p.id)} aria-label={`Delete ${p.title}`}>Delete</button>
                </li>
              ))}
            </ul>
          </MapPanel>
        )}
        {panel === 'home' && (
          <MapPanel
            label="Home" title="Home" onClose={() => setPanel('none')}
            /* Two grid references for two different places, each said out loud. Unlabelled and four
               lines apart, nobody could tell which one was their house and which one the map. Both
               are pinned, because the second of them follows the map you are being asked to aim. */
            lead={
              <>
                <p className="map-ref">Your home: <strong>{homePoint ? gridRef(homePoint.lat, homePoint.lon).text : 'not set yet'}</strong>{homePoint && homePoint.label !== 'Home' ? ` — ${homePoint.label}` : ''}</p>
                <p className="map-ref" role="status">The map is on: <strong>{centreRef.text}</strong></p>
                <p className="map-lead-line">Set as home saves the point the map is on. Move the map and this line follows it.</p>
              </>
            }
            actions={<button type="button" className="btn btn-primary" disabled={savingHome} onClick={() => void saveHome()}>Set as home</button>}
          >
            {homePoint ? (
              <>
                <p>{home?.flood_zone ? <span className="badge badge-warn">▲ Flood zone {home.flood_zone}</span> : <span className="muted">No flood zone recorded.</span>}</p>
                <button type="button" className="btn" onClick={() => flyTo(homePoint.lon, homePoint.lat, 15)}>Go to home</button>
              </>
            ) : (
              <p className="muted">No home set. The box uses it for the sun times, the facilities near you and every distance it quotes.</p>
            )}
            <label className="field"><span>Name</span><input type="text" aria-label="Home name" value={homeLabel} maxLength={60} onChange={(e) => setHomeLabel(e.target.value)} /></label>
            <p className="muted">{overlaysOn?.includes('flood-zones') ? 'The flood zone under the centre is saved with it.' : 'Turn the flood zones layer on first to record the flood zone too.'}</p>
            {homeQ.error && <p className="warning">Home unavailable: {homeQ.error}</p>}
          </MapPanel>
        )}
        {panel === 'nearby' && (
          <MapPanel
            label="Nearby" title="Nearby" onClose={() => setPanel('none')}
            /* The one thing this panel exists to say — the nearest place of the kind you need — is
               pinned above the list. It used to sit below a caveat paragraph and behind the action
               row, so on a phone the nearest hospital was the one line you could not read. */
            lead={
              <>
                {/* Which point the answer was measured from, on the panel, in the same place the
                    answer itself is. */}
                <p className="map-lead-line" role="status">
                  From <strong>{nearbyFromLabel}</strong>, {nearbyAt ? gridRef(nearbyAt.lat, nearbyAt.lon).text : centreRef.text}
                </p>
                {nearbyFacilities.length > 0 && (
                  <select aria-label="Which kind of place do you need?" value={nearbyLead?.id ?? ''} onChange={(e) => setNearbyKind(e.target.value)}>
                    {nearbyFacilities.map((f) => <option key={f.id} value={f.id}>{f.nearest ? f.title : `${f.title} — nothing found`}</option>)}
                  </select>
                )}
                {nearbyQ.loading && <p className="map-lead-line">Looking…</p>}
                {nearbyQ.error && <p className="warning">Nearby facilities unavailable: {nearbyQ.error}</p>}
                {nearbyNearest && nearbyLead && (
                  <>
                    <p className="map-lead-answer">{placeName(nearbyNearest.name, nearbyLead.title)}</p>
                    <p className="map-lead-line">{describeNearby(nearbyNearest)}</p>
                  </>
                )}
                {nearbyLead && !nearbyLead.nearest && <p className="map-lead-line"><span aria-hidden="true">✕</span> {nearbyGap(nearbyLead)}</p>}
                {!nearbyQ.loading && !nearbyQ.error && !nearbyLead && <p className="map-lead-line">Nothing found near here.</p>}
              </>
            }
            actions={
              <>
                {nearbyNearest && <button type="button" className="btn btn-small" onClick={() => flyTo(nearbyNearest.lon, nearbyNearest.lat, 15)}>Show it on the map</button>}
                {/* The other point, named, so the label always says what pressing it would change. */}
                {fromHome
                  ? <button type="button" className="btn btn-small" onClick={() => searchFrom('centre')}>Search from the map centre</button>
                  : homePoint
                    ? <button type="button" className="btn btn-small" onClick={() => searchFrom('home')}>Search from your home</button>
                    : <button type="button" className="btn btn-small" onClick={() => searchFrom('centre')}>Search from this centre</button>}
              </>
            }
          >
            <ul className="list nearby-list" aria-label="Nearby facilities">
              {(nearbyQ.data?.facilities ?? []).map((f) => (
                <li key={f.id} className="nearby-facility">
                  <p className="nearby-kind"><Icon name={nearbyIcon(f.id)} size={20} /> <strong>{f.title}</strong></p>
                  {f.nearest ? (
                    <>
                      <div className="nearby-item">
                        <button type="button" className="btn nearby-go" onClick={() => openFromNearby(f, f.nearest!)}>
                          <span><strong>{placeName(f.nearest.name, f.title)}</strong><small>{describeNearby(f.nearest)}</small></span>
                        </button>
                        <button type="button" className="btn btn-small" onClick={() => setRouteTo({ title: f.nearest!.name, lat: f.nearest!.lat, lon: f.nearest!.lon })} aria-label={`Line to ${f.nearest.name}`}>Line to</button>
                      </div>
                      {f.also.length > 0 && (
                        <ul className="list nearby-also" aria-label={`Other ${f.title.toLowerCase()} nearby`}>
                          {f.also.map((other) => (
                            <li key={`${other.name}:${other.lat},${other.lon}`}>
                              <button type="button" className="btn btn-small nearby-go" onClick={() => openFromNearby(f, other)}>
                                <span>{placeName(other.name, f.title)}<small>{describeNearby(other)}</small></span>
                              </button>
                            </li>
                          ))}
                        </ul>
                      )}
                      {plainNote(f.note) && <p className="muted nearby-note">{plainNote(f.note)}</p>}
                    </>
                  ) : (
                    <p className="muted nearby-note"><span aria-hidden="true">✕</span> {plainNote(nearbyGap(f))}</p>
                  )}
                </li>
              ))}
            </ul>
            {route && (
              <div className="nearby-route" role="status">
                <p><strong>{route.text}</strong></p>
                <button type="button" className="btn btn-small" onClick={() => setRouteTo(null)}>Clear the line</button>
              </div>
            )}
            {/* The small print about how the distances were worked out is worth reading once, so it
                sits under the list rather than in front of the answer. */}
            <p className="muted">Nearest to {fromHome ? 'your home' : nearbyOrigin === 'place' ? nearbyLabel : 'the centre of the map'}, as the crow flies. The walking time is a rough one; the box has no route planner.</p>
          </MapPanel>
        )}
        {panel === 'place' && place && (
          <PlaceCard
            place={place} from={from} guidance={place.kind ? placesQ.data?.[place.kind] ?? null : null}
            onClose={() => { setPanel('none'); setPlace(null); }}
            onRoute={() => setRouteTo({ title: place.title, lat: place.lat, lon: place.lon })}
            onPin={() => { setPendingPin({ lat: place.lat, lon: place.lon }); setPinTitle(place.title); setPanel('pins'); }}
            onNearby={() => { setNearbyOrigin('place'); setNearbyLabel(place.title); setNearbyAt({ lat: place.lat, lon: place.lon }); setPanel('nearby'); }}
          />
        )}
        {panel === 'share' && (
          <MapPanel
            label="Share" title="Share this place" onClose={() => setPanel('none')}
            onBodySize={setShareBody}
            /* One place, written down once. The panel used to give the grid reference in a footer
               and the same place again as latitude and longitude inside a box of link text, which is
               two notations to read for one point on the ground. The link is now a link. */
            lead={<p className="map-ref">The map is on: <strong>{centreRef.text}</strong></p>}
            actions={<button type="button" className="btn btn-primary" onClick={() => void copyLink()}><Icon name="share" size={18} /><span>Copy the link</span></button>}
          >
            <QrCode text={shareUrl} size={shareQrSize} label="Scan to open this place" />
            <a className="share-link" href={shareUrl}>{shareUrl}</a>
            <p className="muted">Point the other phone's camera at the code, or type that address into it.</p>
          </MapPanel>
        )}
      </div>
      <div className="map-readout chrome" data-testid="map-readout">
        <span>Centre: {centreRef.text}</span>
        {tappedRef && <span> · Tapped: {tappedRef.text}</span>}
        {measureText && <span> · {measureText}</span>}
        {route && <span> · {route.text}</span>}
      </div>
      {printImage && (
        <div className="map-print">
          <img src={printImage} alt="Map" onLoad={() => { window.print(); setPrintImage(null); }} />
          <p>Centre {centreRef.text} ({centreRef.system}) · zoom {view.zoom.toFixed(1)}</p>
          <ul>{legend.map((o) => <li key={o.id}><span className="swatch" style={{ background: o.color }} /> {o.title}</li>)}</ul>
          <p>Printed from Operation SOS. Scale bar as shown on screen at this zoom.</p>
        </div>
      )}
    </Screen>
  );
}
