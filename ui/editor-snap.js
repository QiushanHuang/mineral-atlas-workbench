(function (root) {
  'use strict';

  // Geometry stays in original display pixels. Only pickSnap converts distances
  // to CSS pixels; devicePixelRatio must not enter the radius calculation.
  const EPSILON = 1e-6;
  const MAX_INPUT_POINTS = 8192;
  const PRIORITY = {start: 0, vertex: 1, intersection: 2, midpoint: 3, image_corner: 4};
  const LABELS = {start: '闭合起点', vertex: '已标端点', intersection: '线段交点', midpoint: '线段中点', image_corner: '本地图像候选角点（未确认）'};
  const pointOK = point => Array.isArray(point) && point.length === 2 && point.every(value => Number.isFinite(value) && Math.abs(value) <= 1e9);
  const pointKey = point => point.map(value => String(Object.is(value, -0) ? 0 : value)).join(',');
  const lexical = (a, b) => a < b ? -1 : a > b ? 1 : 0;
  const priority = target => PRIORITY[target.kind] ?? 99;
  const order = (a, b) => priority(a) - priority(b) || lexical(a.id, b.id) || a.point[0] - b.point[0] || a.point[1] - b.point[1];
  const limit = (value, fallback, maximum) => Number.isInteger(value) && value >= 0 ? Math.min(value, maximum) : fallback;
  const cross = (a, b) => a[0] * b[1] - a[1] * b[0];

  function intersection(first, second) {
    const a = first.a, b = first.b, c = second.a, d = second.b;
    const u = [b[0] - a[0], b[1] - a[1]], v = [d[0] - c[0], d[1] - c[1]];
    const lengths = Math.hypot(...u) * Math.hypot(...v), determinant = cross(u, v);
    // Collinear and near-parallel lines do not give a reliable point target.
    if (!Number.isFinite(lengths) || lengths <= EPSILON * EPSILON || Math.abs(determinant) / lengths < 1e-4) return null;
    const offset = [c[0] - a[0], c[1] - a[1]];
    const t = cross(offset, v) / determinant, s = cross(offset, u) / determinant;
    if (t < 0 || t > 1 || s < 0 || s > 1) return null; // Never extend a segment.
    const point = [a[0] + t * u[0], a[1] + t * u[1]];
    return pointOK(point) ? point : null;
  }

  function proposeTargets(annotation, workingPoints = [], imageHints = [], settings = {}) {
    settings = settings && typeof settings === 'object' ? settings : {};
    const maxSegments = limit(settings.maxSegments, 256, 256);
    const maxTargets = limit(settings.maxTargets, 4096, 8192);
    const meta = {truncated: false, segments_seen: 0, segments_used: 0, targets_returned: 0, intersections_tested: 0, truncated_reasons: []};
    function truncated(reason) {
      meta.truncated = true;
      if (!meta.truncated_reasons.includes(reason)) meta.truncated_reasons.push(reason);
    }
    const size = annotation && pointOK(annotation.image_size) && annotation.image_size.every(value => value > 0) ? annotation.image_size : null;
    const valid = point => pointOK(point) && (!size || point.every((value, index) => value >= 0 && value <= size[index]));
    const rawFeatures = Array.isArray(annotation?.features) ? annotation.features : [];
    if (rawFeatures.length > 512) truncated('input_features');
    const features = rawFeatures.slice(0, 512).filter(feature => feature && typeof feature.id === 'string' && /^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$/.test(feature.id) && Array.isArray(feature.points))
      .map(feature => ({id: feature.id, kind: feature.kind, points: feature.points}))
      .sort((a, b) => lexical(a.id, b.id) || lexical(String(a.kind), String(b.kind)));
    const vertices = [], segments = [];
    let pointsRead = 0;
    for (const feature of features) {
      const remaining = Math.max(0, MAX_INPUT_POINTS - pointsRead);
      if (feature.points.length > remaining) truncated('input_points');
      const points = feature.points.slice(0, remaining).map(point => valid(point) ? [...point] : null);
      pointsRead += points.length;
      points.forEach((point, index) => {
        if (point) vertices.push({id: `vertex:${feature.id}:${index}`, point, kind: 'vertex', label: LABELS.vertex, featureId: feature.id, pointIndex: index});
      });
      if (!['edge', 'silhouette', 'face'].includes(feature.kind)) continue;
      const closed = feature.kind !== 'edge' && points.length >= 3 && points.length === feature.points.length;
      for (let i = 0; i < points.length - (closed ? 0 : 1); i++) {
        const a = points[i], b = points[(i + 1) % points.length];
        if (!a || !b || Math.hypot(a[0] - b[0], a[1] - b[1]) <= EPSILON) continue;
        meta.segments_seen++;
        if (segments.length < maxSegments) segments.push({id: `${feature.id}:${i}`, a, b, featureId: feature.id});
        else truncated('segments');
      }
    }
    segments.sort((a, b) => lexical(a.id, b.id));
    meta.segments_used = segments.length;

    // Deterministic priority phases plus a spatial grid coalesce coincident targets
    // without a quadratic scan of all 2048 annotated points.
    const targets = [], cells = new Map();
    function add(target) {
      if (!valid(target.point)) return;
      const x = Math.floor(target.point[0] / EPSILON), y = Math.floor(target.point[1] / EPSILON);
      for (let dx = -1; dx <= 1; dx++) for (let dy = -1; dy <= 1; dy++) {
        const nearby = cells.get(`${x + dx},${y + dy}`) || [];
        if (nearby.some(other => Math.hypot(other.point[0] - target.point[0], other.point[1] - target.point[1]) <= EPSILON)) return;
      }
      if (targets.length >= maxTargets) { truncated('targets'); return; }
      const key = `${x},${y}`, bucket = cells.get(key) || [];
      bucket.push(target); cells.set(key, bucket); targets.push(target);
    }
    if (settings.includeStart === true && Array.isArray(workingPoints) && workingPoints.length >= 3 && valid(workingPoints[0])) {
      add({id: 'start:0', point: [...workingPoints[0]], kind: 'start', label: LABELS.start});
    }
    vertices.sort(order).forEach(add);
    if (settings.includeIntersections !== false) {
      for (let i = 0; i < segments.length; i++) {
        if (targets.length >= maxTargets) { if (segments.length > 1) truncated('targets'); break; }
        for (let j = i + 1; j < segments.length; j++) {
          if (targets.length >= maxTargets) { truncated('targets'); break; }
          meta.intersections_tested++;
          const point = intersection(segments[i], segments[j]);
          if (point) add({id: `intersection:${segments[i].id}|${segments[j].id}`, point, kind: 'intersection', label: LABELS.intersection});
        }
      }
    }
    if (settings.includeMidpoints !== false) {
      for (const segment of segments) add({id: `midpoint:${segment.id}`, point: [(segment.a[0] + segment.b[0]) / 2, (segment.a[1] + segment.b[1]) / 2], kind: 'midpoint', label: LABELS.midpoint, featureId: segment.featureId});
    }
    if (settings.includeImageCorners === true && Array.isArray(imageHints)) {
      const minimum = Number.isFinite(settings.minImageConfidence) ? settings.minImageConfidence : .75;
      if (imageHints.length > 4096) truncated('image_hints');
      const hints = [];
      for (const hint of imageHints.slice(0, 4096)) {
        const point = Array.isArray(hint) ? hint : hint?.point;
        if (!valid(point)) continue;
        if (!Array.isArray(hint) && hint.confidence !== undefined && (!Number.isFinite(hint.confidence) || hint.confidence < minimum)) continue;
        const id = !Array.isArray(hint) && typeof hint.id === 'string' && /^[A-Za-z0-9_-]{1,64}$/.test(hint.id) ? `${hint.id}:` : '';
        hints.push({id: `image_corner:${id}${pointKey(point)}`, point: [...point], kind: 'image_corner', label: LABELS.image_corner});
      }
      hints.sort(order).forEach(add);
    }
    targets.sort(order);
    meta.targets_returned = targets.length;
    Object.defineProperty(targets, 'meta', {value: meta, enumerable: false});
    return targets;
  }

  function pickSnap(rawPoint, targets, options = {}) {
    if (!Array.isArray(rawPoint) || rawPoint.length !== 2 || !rawPoint.every(Number.isFinite)) throw new TypeError('rawPoint 必须是两个有限数值');
    const unchanged = () => ({point: [...rawPoint], target: null, distance_px: null});
    options = options && typeof options === 'object' ? options : {};
    if (options.enabled === false || options.bypass === true) return unchanged();
    const scale = options.scale === undefined ? 1 : options.scale, radius = options.radius === undefined ? 12 : options.radius;
    if (!Number.isFinite(scale) || scale <= 0 || !Number.isFinite(radius) || radius < 0 || !Array.isArray(targets)) return unchanged();
    const exclude = new Set(Array.isArray(options.exclude) || options.exclude instanceof Set ? options.exclude : []);
    let best = null;
    for (const target of targets) {
      if (!target || typeof target.id !== 'string' || exclude.has(target.id) || !pointOK(target.point)) continue;
      const distance = Math.hypot((target.point[0] - rawPoint[0]) * scale, (target.point[1] - rawPoint[1]) * scale);
      if (!Number.isFinite(distance) || distance > radius) continue;
      if (!best || distance < best.distance - 1e-9 || (Math.abs(distance - best.distance) <= 1e-9 && order(target, best.target) < 0)) best = {target, distance};
    }
    return best ? {point: [...best.target.point], target: {...best.target, point: [...best.target.point]}, distance_px: best.distance} : unchanged();
  }

  const api = {proposeTargets, pickSnap};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.AtlasEditorSnap = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
