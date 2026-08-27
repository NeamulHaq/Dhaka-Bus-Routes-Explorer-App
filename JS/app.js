(function(){
'use strict';

var map=L.map('map',{zoomControl:false,minZoom:9,maxZoom:18}).setView([23.79,90.41],11);
L.control.zoom({position:'bottomright'}).addTo(map);
L.control.scale({position:'bottomright',imperial:false}).addTo(map);
L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{   subdomains: 'abcd',   maxZoom: 20,   crossOrigin: 'anonymous',   attribution: '© OpenStreetMap contributors © CARTO',   opacity: 0.6 }).addTo(map);

var selectedLayer=null,selectedRoutes=[],selectedStops=[];
var routeLayerById={};
var toolMode=null,drawMode=null,measurePoints=[],measureLayer=L.layerGroup().addTo(map),polygonVertices=[],polygonLayer=null;
var tempLayer=L.layerGroup().addTo(map),tempRoutes=[],tempPoints=[],tempActiveRoute=null,tempVertexHandles=L.layerGroup().addTo(map),tempEditMode=null;
var detail=document.getElementById('detail'),detailBody=document.getElementById('detailBody');
var tableState={tab:'routes',query:''};

function setStatus(s){var e=document.getElementById('toolStatus');if(e)e.textContent=s;}
function safe(v){return String(v==null?'':v).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
function num(v,d){var x=Number(v);return isFinite(x)?x.toLocaleString(undefined,{maximumFractionDigits:d==null?1:d}):'—';}
function isAC(p){var t=String(p['Bus Type']||'').toUpperCase();return t.indexOf('AC')>=0&&t.indexOf('NON')<0;}
function routeColor(p){return isAC(p)?'#0E7C86':'#2B6CB0';}
function baseStyle(f){return {color:routeColor(f.properties||{}),weight:2.2,opacity:.62};}
function selectedStyle(){return {color:'#E4572E',weight:5,opacity:1};}
function alignParts(p){return String(p['Alingment']||'').split('?').map(function(x){return x.trim();}).filter(Boolean);}
function normalize(s){return String(s||'').toLowerCase().replace(/[–—]/g,'-').replace(/[^a-z0-9]+/g,'').trim();}
function fareForKm(km){var raw=Math.max(10,Number(km||0)*2.53);return Math.max(10,Math.ceil(raw/5)*5);}
function hav(a,b){return map.distance(L.latLng(a.lat,a.lng),L.latLng(b.lat,b.lng));}
function routeStops(f){var rid=f.properties.Route_ID,st=STOPS_DATA.filter(function(s){return String(s.route_id)===String(rid);}).map(function(s){return Object.assign({},s);}),c=f.geometry.coordinates||[];if(c.length<2)return st;function idx(s){var best=1e99,bi=0;c.forEach(function(x,i){var dx=(x[0]-s.lng)*Math.cos(s.lat*Math.PI/180),dy=x[1]-s.lat,d=dx*dx+dy*dy;if(d<best){best=d;bi=i;}});return bi;}st.forEach(function(s){s._i=idx(s);});st.sort(function(a,b){return a._i-b._i;});return st;}

/* Read-only source layers */
var adminLayer=L.geoJSON(ADMIN_DATA,{style:function(){return {color:'#9fb0c2',weight:1,fillColor:'#c9d3de',fillOpacity:.10,opacity:.55};}});
var corridorLayer=L.geoJSON(CORRIDORS_DATA,{style:function(){return {color:'#B9860A',weight:2,dashArray:'6 5',opacity:.7};}}).addTo(map);
var routesLayer=L.geoJSON(ROUTES_DATA,{style:baseStyle,onEachFeature:function(f,l){var id=f.properties.Route_ID;routeLayerById[id]=l;l.on('mouseover',function(){if(l!==selectedLayer)l.setStyle({color:routeColor(f.properties),weight:4.5,opacity:.95});});l.on('mouseout',function(){if(l!==selectedLayer)l.setStyle(baseStyle(f));});l.on('click',function(e){L.DomEvent.stopPropagation(e);selectRoute(f,l);});}}).addTo(map);
var stopCluster=L.markerClusterGroup({maxClusterRadius:38,showCoverageOnHover:false,disableClusteringAtZoom:15}),stopMarkers=[];
STOPS_DATA.forEach(function(s){var m=L.circleMarker([s.lat,s.lng],{radius:5,color:'#fff',weight:1.4,fillColor:'#122240',fillOpacity:.95});m._stopRef=s;m.bindTooltip(s.name,{direction:'top',offset:[0,-4]});m.on('click',function(e){L.DomEvent.stopPropagation(e);selectStop(s,m);});stopMarkers.push(m);stopCluster.addLayer(m);});
stopCluster.addTo(map);

function clearSelection(){if(selectedLayer){selectedLayer.setStyle(baseStyle(selectedLayer.feature));selectedLayer=null;}selectedRoutes=[];selectedStops=[];stopMarkers.forEach(function(m){m._selected=false;m.setStyle({fillColor:'#122240',radius:5});});updateJpegButton();}
function openDetail(){detail.classList.add('open');}
function closeDetail(){detail.classList.remove('open');clearSelection();}
document.getElementById('detailCloseBtn').onclick=closeDetail;
function selectRoute(f,l){clearSelection();selectedLayer=l;selectedRoutes=[f];l.setStyle(selectedStyle());l.bringToFront();map.fitBounds(l.getBounds(),{paddingTopLeft:[320,40],paddingBottomRight:[360,40]});renderRouteDetail(f);updateJpegButton();}
function selectStop(s,m){clearSelection();selectedStops=[s];m._selected=true;m.setStyle({fillColor:'#E4572E',radius:7});map.setView([s.lat,s.lng],Math.max(15,map.getZoom()));var rl=routeLayerById[s.route_id];detailBody.innerHTML='<div class="dp-head"><button class="dp-close" id="detailCloseBtn2">×</button><div class="dp-kind">Bus Stop · Read Only</div><div class="dp-title">'+safe(s.name)+'</div><div class="dp-sub">Route '+safe(s.route_id||'—')+'</div></div><div class="dp-block"><h4>Location</h4><div class="op-row"><span class="k">Latitude</span><span class="v mono">'+s.lat.toFixed(6)+'</span></div><div class="op-row"><span class="k">Longitude</span><span class="v mono">'+s.lng.toFixed(6)+'</span></div></div><div class="read-only-note">GeoJSON data are read-only. Existing stops cannot be edited.</div>';document.getElementById('detailCloseBtn2').onclick=closeDetail;openDetail();updateJpegButton();}
function renderRouteDetail(f){var p=f.properties||{},st=routeStops(f),path=alignParts(p).map(function(x,i){return '<span class="stop-chip">'+safe(x)+'</span>'+(i<alignParts(p).length-1?'<span class="arrow">→</span>':'');}).join('');detailBody.innerHTML='<div class="dp-head"><button class="dp-close" id="detailCloseBtn2">×</button><div class="dp-kind">Bus Route · Read Only</div><div class="dp-title">'+safe(p.Route_ID)+'</div><div class="dp-sub">'+safe(p.Operator||'Operator not recorded')+'</div></div><div class="stub"><div class="stub-top"><span class="rid">'+safe(p.Route_ID)+'</span><span class="badge '+(isAC(p)?'ac':'nonac')+'">'+safe(p['Bus Type']||'—')+'</span></div><div class="stub-grid"><div class="stub-cell"><div class="v">'+num(p.Length,1)+' km</div><div class="k">Route Length</div></div><div class="stub-cell"><div class="v">'+num(p.Headway,0)+' min</div><div class="k">Headway</div></div><div class="stub-cell"><div class="v">'+num(p['Actual Bus'],0)+'</div><div class="k">Buses Operating</div></div><div class="stub-cell"><div class="v">'+num(p['Permitted '],0)+'</div><div class="k">Permitted Fleet</div></div><div class="stub-cell"><div class="v">'+Math.round(Number(p['No of Trip'])||0)+'</div><div class="k">Trips / Day</div></div><div class="stub-cell"><div class="v">'+num(p['Travel Tim'],0)+' min</div><div class="k">Travel Time</div></div></div></div><div class="dp-block"><h4>Alignment</h4><div class="route-path">'+(path||'<span style="color:var(--muted)">Not recorded</span>')+'</div></div><div class="dp-block"><h4>Mapped Stops on This Route ('+st.length+')</h4><div id="routeStopList">'+(st.length?st.map(function(s,i){return '<div class="stop-list-item" data-lat="'+s.lat+'" data-lng="'+s.lng+'"><span class="sname">'+(i+1)+'. '+safe(s.name)+'</span><span class="sid mono">'+s.lat.toFixed(4)+', '+s.lng.toFixed(4)+'</span></div>';}).join(''):'<div style="color:var(--muted);font-size:12px">No individually mapped stops recorded.</div>')+'</div></div><div class="read-only-note">Official GeoJSON route and attributes are view-only. Use Draw to create temporary user features.</div>';document.getElementById('detailCloseBtn2').onclick=closeDetail;Array.prototype.forEach.call(detailBody.querySelectorAll('.stop-list-item'),function(e){e.onclick=function(){map.setView([+e.dataset.lat,+e.dataset.lng],16);};});openDetail();}

/* Layer toggles */
[['toggleRoutes',routesLayer],['toggleStops',stopCluster],['toggleCorridors',corridorLayer],['toggleAdmin',adminLayer]].forEach(function(x){document.getElementById(x[0]).onchange=function(e){if(e.target.checked)map.addLayer(x[1]);else map.removeLayer(x[1]);};});
document.getElementById('resetBtn').onclick=function(){map.setView([23.79,90.41],11);closeDetail();};

/* Search */
var searchBox=document.getElementById('searchBox'),searchResults=document.getElementById('searchResults');
function runSearch(q){q=normalize(q);searchResults.innerHTML='';if(!q)return;ROUTES_DATA.features.filter(function(f){var p=f.properties||{};return normalize(p.Route_ID).indexOf(q)>=0||normalize(p.Operator).indexOf(q)>=0||alignParts(p).some(function(a){return normalize(a).indexOf(q)>=0;});}).slice(0,20).forEach(function(f){var p=f.properties,row=document.createElement('div');row.className='result-row';row.innerHTML='<span class="rid mono">'+safe(p.Route_ID)+'</span><span class="rname">'+safe(p.Operator||'')+'</span>';row.onclick=function(){selectRoute(f,routeLayerById[p.Route_ID]);};searchResults.appendChild(row);});}
searchBox.oninput=function(){runSearch(searchBox.value);};

/* Measure */
function clearMeasure(){measureLayer.clearLayers();measurePoints=[];setStatus('Measurement cleared.');}
document.getElementById('measureBtn').onclick=function(){toolMode=toolMode==='measure'?null:'measure';polygonVertices=[];if(toolMode==='measure'){clearMeasure();setStatus('Measure: click points; double-click to finish.');}else{clearMeasure();setStatus('Ready.');}};
function dist(points){var d=0;for(var i=1;i<points.length;i++)d+=map.distance(points[i-1],points[i]);return d;}
function area(points){var R=6378137;if(points.length<3)return 0;var a=0;for(var i=0;i<points.length;i++){var p=points[i],q=points[(i+1)%points.length];var x1=R*Math.PI*p.lng/180*Math.cos(p.lat*Math.PI/180),y1=R*Math.PI*p.lat/180;var x2=R*Math.PI*q.lng/180*Math.cos(q.lat*Math.PI/180),y2=R*Math.PI*q.lat/180;a+=x1*y2-x2*y1;}return Math.abs(a/2);}
map.on('click',function(e){if(toolMode==='measure'){measurePoints.push(e.latlng);L.circleMarker(e.latlng,{radius:4,color:'#E4572E',weight:2,fillColor:'#fff',fillOpacity:1}).addTo(measureLayer);if(measurePoints.length>1){var line=L.polyline(measurePoints,{color:'#E4572E',weight:3,dashArray:'6 4'}).addTo(measureLayer);setStatus('Distance: '+(dist(measurePoints)/1000).toFixed(2)+' km'+(measurePoints.length>2?' · Area: '+(area(measurePoints)/1000000).toFixed(3)+' km²':''));}return;}
if(toolMode==='polygon'){polygonVertices.push(e.latlng);if(polygonLayer)map.removeLayer(polygonLayer);polygonLayer=L.polygon(polygonVertices,{color:'#2B6CB0',weight:2,dashArray:'6 5',fillOpacity:.1}).addTo(map);setStatus('Select polygon: '+polygonVertices.length+' vertices; double-click to finish.');return;}
if(toolMode==='draw'&&drawMode==='point'){addTempPoint(e.latlng);return;}
if(toolMode==='draw'&&drawMode==='route'){addTempRouteVertex(e.latlng);return;}});
map.on('dblclick',function(e){if(toolMode==='measure'){setStatus('Measurement complete: '+(dist(measurePoints)/1000).toFixed(2)+' km.');L.DomEvent.stopPropagation(e);}else if(toolMode==='polygon'){finishPolygon();L.DomEvent.stopPropagation(e);}else if(toolMode==='draw'&&drawMode==='route'){finishTempRoute();L.DomEvent.stopPropagation(e);}});

/* Polygon selection: read-only selection only */
document.getElementById('selectPolyBtn').onclick=function(){toolMode=toolMode==='polygon'?null:'polygon';polygonVertices=[];if(polygonLayer){map.removeLayer(polygonLayer);polygonLayer=null;}if(toolMode==='polygon')setStatus('Select by Polygon: draw around routes/stops; double-click to finish.');else{clearSelection();setStatus('Ready.');}};
function finishPolygon(){if(polygonVertices.length<3){setStatus('At least 3 vertices are required.');return;}clearSelection();ROUTES_DATA.features.forEach(function(f){if(lineIntersectsPolygon(f.geometry.coordinates,polygonVertices)){selectedRoutes.push(f);var l=routeLayerById[f.properties.Route_ID];if(l){l.setStyle(selectedStyle());selectedLayer=l;}}});STOPS_DATA.forEach(function(s){if(pointInPoly(s.lat,s.lng,polygonVertices)){selectedStops.push(s);var m=stopMarkers.find(function(x){return x._stopRef===s;});if(m)m.setStyle({fillColor:'#E4572E',radius:7});}});toolMode=null;if(polygonLayer){map.removeLayer(polygonLayer);polygonLayer=null;}setStatus('Selected '+selectedRoutes.length+' route(s) and '+selectedStops.length+' stop(s). GeoJSON remains read-only.');updateJpegButton();}
function pointInPoly(lat,lng,poly){var inside=false;for(var i=0,j=poly.length-1;i<poly.length;j=i++){var xi=poly[i].lng,yi=poly[i].lat,xj=poly[j].lng,yj=poly[j].lat,inter=((yi>lat)!=(yj>lat))&&(lng<(xj-xi)*(lat-yi)/(yj-yi)+xi);if(inter)inside=!inside;}return inside;}
function lineIntersectsPolygon(coords,poly){return coords.some(function(c){return pointInPoly(c[1],c[0],poly);})||poly.some(function(p){return coords.some(function(c){return map.distance([p.lat,p.lng],[c[1],c[0]])<120;});});}

/* Temporary drawing only */
document.getElementById('drawBtn').onclick=function(){var open=!document.getElementById('drawSubtools').classList.contains('open');document.getElementById('drawSubtools').classList.toggle('open',open);toolMode=open?'draw':null;setStatus(open?'Draw mode: create temporary routes/stops; they can be edited or deleted and never change GeoJSON.':'Ready.');};
document.getElementById('drawRouteBtn').onclick=function(){toolMode='draw';drawMode='route';tempActiveRoute={name:'Temporary Route '+(tempRoutes.length+1),latlngs:[]};setStatus('Draw Route: click vertices, double-click to finish.');};
document.getElementById('drawPointBtn').onclick=function(){toolMode='draw';drawMode='point';setStatus('Draw Point: click map to create a temporary stop.');};
document.getElementById('clearDrawBtn').onclick=function(){tempLayer.clearLayers();tempVertexHandles.clearLayers();tempRoutes=[];tempPoints=[];tempActiveRoute=null;tempEditMode=null;setStatus('Temporary drawings cleared. Official GeoJSON was not changed.');updateJpegButton();};
function addTempRouteVertex(ll){if(!tempActiveRoute){tempActiveRoute={name:'Temporary Route '+(tempRoutes.length+1),latlngs:[]};}tempActiveRoute.latlngs.push(ll);redrawTempRoutePreview();setStatus('Temporary route vertices: '+tempActiveRoute.latlngs.length+'. Double-click to finish.');}
function redrawTempRoutePreview(){tempLayer.eachLayer(function(l){if(l._preview)tempLayer.removeLayer(l);});if(tempActiveRoute&&tempActiveRoute.latlngs.length){var l=L.polyline(tempActiveRoute.latlngs,{color:'#7c3aed',weight:5,dashArray:'10 6',opacity:.95});l._preview=true;tempLayer.addLayer(l);}}
function finishTempRoute(){if(tempActiveRoute&&tempActiveRoute.latlngs.length>2){var a=tempActiveRoute.latlngs[tempActiveRoute.latlngs.length-2],b=tempActiveRoute.latlngs[tempActiveRoute.latlngs.length-1];if(map.distance(a,b)<18)tempActiveRoute.latlngs.pop();}if(!tempActiveRoute||tempActiveRoute.latlngs.length<2){setStatus('A temporary route needs at least two vertices.');return;}var name=prompt('Temporary route name:',tempActiveRoute.name);if(name===null)name=tempActiveRoute.name;var r={id:'temp-route-'+Date.now(),name:name,latlngs:tempActiveRoute.latlngs.slice()};tempRoutes.push(r);tempActiveRoute=null;tempLayer.eachLayer(function(l){if(l._preview)tempLayer.removeLayer(l);});renderTempRoutes();setStatus('Temporary route created: '+name+'.');}
function renderTempRoutes(){tempLayer.eachLayer(function(l){if(l._temp)tempLayer.removeLayer(l);});tempRoutes.forEach(function(r){var l=L.polyline(r.latlngs,{color:'#7c3aed',weight:5,dashArray:'10 6',opacity:.95});l._temp=true;l._tempId=r.id;l.bindTooltip(r.name,{sticky:true,className:'draw-label'});l.on('click',function(e){if(toolMode==='draw'&&tempEditMode){L.DomEvent.stopPropagation(e);if(tempEditMode==='add')addTempVertexAtClick(r,e.latlng);else if(tempEditMode==='deleteFeature'){tempRoutes=tempRoutes.filter(function(x){return x.id!==r.id;});clearTempHandles();renderTempRoutes();setStatus('Temporary route deleted.');}else editTempRoute(r);}});l.on('mousedown',function(e){if(toolMode==='draw'&&tempEditMode==='move'){startTempRouteMove(r,e);L.DomEvent.stopPropagation(e);}});tempLayer.addLayer(l);});}

function nearestTempSegment(r,ll){var best={d:Infinity,i:-1,pt:null};for(var i=0;i<r.latlngs.length-1;i++){var a=r.latlngs[i],b=r.latlngs[i+1],t=0;var dx=b.lng-a.lng,dy=b.lat-a.lat;var denom=dx*dx+dy*dy;if(denom>0)t=((ll.lng-a.lng)*dx+(ll.lat-a.lat)*dy)/denom;t=Math.max(0,Math.min(1,t));var pt=L.latLng(a.lat+(b.lat-a.lat)*t,a.lng+(b.lng-a.lng)*t),d=map.distance(ll,pt);if(d<best.d)best={d:d,i:i,pt:pt};}return best;}
function addTempVertexAtClick(r,ll){var b=nearestTempSegment(r,ll);if(b.i<0||b.d>80){setStatus('Click closer to a temporary route segment to add a vertex.');return;}r.latlngs.splice(b.i+1,0,b.pt);renderTempRoutes();editTempRoute(r);setStatus('Temporary route vertex added.');}
function startTempRouteMove(r,e){var start=e.latlng,original=r.latlngs.map(function(x){return L.latLng(x.lat,x.lng);});function moving(ev){var dLat=ev.latlng.lat-start.lat,dLng=ev.latlng.lng-start.lng;r.latlngs=original.map(function(x){return L.latLng(x.lat+dLat,x.lng+dLng);});renderTempRoutes();}function done(){map.off('mousemove',moving);map.off('mouseup',done);setStatus('Temporary route moved.');}map.on('mousemove',moving);map.once('mouseup',done);}
function deleteTempFeatureAtClick(){setStatus('Click a temporary route or stop to delete it.');tempEditMode='deleteFeature';}

function addTempPoint(ll){var name=prompt('Temporary stop name:','Temporary Stop '+(tempPoints.length+1));if(name===null)name='Temporary Stop '+(tempPoints.length+1);var p={id:'temp-point-'+Date.now(),name:name,lat:ll.lat,lng:ll.lng};tempPoints.push(p);renderTempPoints();setStatus('Temporary stop created: '+name+'.');}
function renderTempPoints(){tempLayer.eachLayer(function(l){if(l._tempPoint)tempLayer.removeLayer(l);});tempPoints.forEach(function(p){var m=L.circleMarker([p.lat,p.lng],{radius:7,color:'#fff',weight:2,fillColor:'#7c3aed',fillOpacity:.95});m._tempPoint=true;m._tempId=p.id;m.bindTooltip(p.name,{permanent:true,direction:'top',offset:[0,-7],className:'draw-label'});m.on('click',function(e){if(toolMode==='draw'&&tempEditMode){L.DomEvent.stopPropagation(e);if(tempEditMode==='deleteFeature'){tempPoints=tempPoints.filter(function(x){return x.id!==p.id;});renderTempPoints();setStatus('Temporary stop deleted.');}else editTempPoint(p,m);}});tempLayer.addLayer(m);});}
function editTempRoute(r){clearTempHandles();tempEditMode='route';tempVertexHandles._routeId=r.id;r.latlngs.forEach(function(ll,i){var h=L.marker(ll,{draggable:true,icon:L.divIcon({className:'temp-vertex',html:'<span></span>',iconSize:[14,14],iconAnchor:[7,7]})}).addTo(tempVertexHandles);h.on('drag',function(){r.latlngs[i]=h.getLatLng();renderTempRoutes();});h.on('click',function(e){if(tempEditMode==='delete'){if(r.latlngs.length<=2){setStatus('A temporary route must keep at least two vertices.');return;}r.latlngs.splice(i,1);clearTempHandles();renderTempRoutes();setStatus('Temporary route vertex deleted.');L.DomEvent.stopPropagation(e);}});});setStatus('Temporary route selected. Drag purple vertices.');}
function editTempPoint(p,m){clearTempHandles();tempEditMode='point';m.dragging.enable();m.once('dragend',function(){var ll=m.getLatLng();p.lat=ll.lat;p.lng=ll.lng;renderTempPoints();setStatus('Temporary stop moved.');});setStatus('Temporary stop selected. Drag it to move.');}
function clearTempHandles(){tempVertexHandles.clearLayers();}
document.getElementById('editBtn').onclick=function(){var open=!document.getElementById('editSubtools').classList.contains('open');document.getElementById('editSubtools').classList.toggle('open',open);toolMode=open?'draw':null;tempEditMode=open?'route':null;setStatus(open?'Edit mode applies ONLY to temporary user drawings. Select a temporary route/stop.':'Ready.');};
document.getElementById('moveFeatureBtn').onclick=function(){tempEditMode='move';clearTempHandles();setStatus('Temporary Move: drag a purple route or stop.');};
document.getElementById('vertexEditBtn').onclick=function(){tempEditMode='route';setStatus('Temporary route edit: click a purple route to show draggable vertices.');};
document.getElementById('addVertexBtn').onclick=function(){tempEditMode='add';clearTempHandles();setStatus('Temporary route: click a purple route segment to add a vertex.');};
document.getElementById('deleteVertexBtn').onclick=function(){tempEditMode='delete';setStatus('Temporary route: click Vertices first, then click a purple vertex to delete it.');};
document.getElementById('editAttrBtn').onclick=function(){setStatus('Official GeoJSON attributes are read-only. Temporary drawings use their name only.');};
document.getElementById('editStopBtn').onclick=function(){tempEditMode='point';setStatus('Temporary stop edit: click a purple stop and drag it.');};
document.getElementById('deleteTempBtn').onclick=function(){tempEditMode='deleteFeature';clearTempHandles();setStatus('Delete Temporary: click a purple route or stop.');};

/* Attribute table - view only */
function openTable(){document.getElementById('attributeTable').classList.add('open');updateTable();}
document.getElementById('tableBtn').onclick=openTable;document.getElementById('tableCloseBtn').onclick=function(){document.getElementById('attributeTable').classList.remove('open');};
document.getElementById('tableSearch').oninput=function(e){tableState.query=e.target.value;updateTable();};
document.getElementById('routesTab').onclick=function(){tableState.tab='routes';this.classList.add('active');document.getElementById('stopsTab').classList.remove('active');updateTable();};
document.getElementById('stopsTab').onclick=function(){tableState.tab='stops';this.classList.add('active');document.getElementById('routesTab').classList.remove('active');updateTable();};
function updateTable(){var body=document.getElementById('attributeTableBody'),q=normalize(tableState.query),data;if(tableState.tab==='routes'){data=ROUTES_DATA.features.filter(function(f){return !q||normalize(JSON.stringify(f.properties)).indexOf(q)>=0;}).slice(0,500);document.getElementById('attributeTableHead').innerHTML='<th>Route ID</th><th>Operator</th><th>Bus Type</th><th>Length km</th><th>Trips / Day</th><th>Travel min</th>';body.innerHTML=data.map(function(f){var p=f.properties;return '<tr data-route="'+safe(p.Route_ID)+'"><td>'+safe(p.Route_ID)+'</td><td>'+safe(p.Operator)+'</td><td>'+safe(p['Bus Type'])+'</td><td>'+num(p.Length,1)+'</td><td>'+Math.round(Number(p['No of Trip'])||0)+'</td><td>'+num(p['Travel Tim'],0)+'</td></tr>';}).join('')||'<tr><td colspan="6">No records.</td></tr>';body.querySelectorAll('tr[data-route]').forEach(function(tr){tr.onclick=function(){var f=ROUTES_DATA.features.find(function(x){return String(x.properties.Route_ID)===tr.dataset.route;});if(f)selectRoute(f,routeLayerById[tr.dataset.route]);};});}else{data=STOPS_DATA.filter(function(s){return !q||normalize(JSON.stringify(s)).indexOf(q)>=0;}).slice(0,500);document.getElementById('attributeTableHead').innerHTML='<th>Stop</th><th>Route ID</th><th>Latitude</th><th>Longitude</th>';body.innerHTML=data.map(function(s){return '<tr data-stop="'+safe(s.name)+'"><td>'+safe(s.name)+'</td><td>'+safe(s.route_id)+'</td><td>'+s.lat.toFixed(6)+'</td><td>'+s.lng.toFixed(6)+'</td></tr>';}).join('')||'<tr><td colspan="4">No records.</td></tr>';body.querySelectorAll('tr[data-stop]').forEach(function(tr){tr.onclick=function(){var s=STOPS_DATA.find(function(x){return x.name===tr.dataset.stop;});var m=stopMarkers.find(function(x){return x._stopRef===s;});if(s&&m)selectStop(s,m);};});}document.getElementById('tableRecordCount').textContent=data.length+' records';}

/* Recommendation — origin/destination are read directly from the official stops layer */
function routeGeometryCoords(f){
  var g=f.geometry||{};
  if(g.type==='LineString') return g.coordinates||[];
  if(g.type==='MultiLineString'){
    var best=[]; (g.coordinates||[]).forEach(function(part){ if(part.length>best.length) best=part; });
    return best;
  }
  return [];
}
function projectPointOnRoute(coords,ll){
  var best={d:Infinity,seg:0,t:0,pt:null,along:0};
  var cumulative=0;
  for(var i=0;i<coords.length-1;i++){
    var a=L.latLng(coords[i][1],coords[i][0]), b=L.latLng(coords[i+1][1],coords[i+1][0]);
    var dx=b.lng-a.lng,dy=b.lat-a.lat,den=dx*dx+dy*dy,t=0;
    if(den>0)t=((ll.lng-a.lng)*dx+(ll.lat-a.lat)*dy)/den;
    t=Math.max(0,Math.min(1,t));
    var pt=L.latLng(a.lat+(b.lat-a.lat)*t,a.lng+(b.lng-a.lng)*t);
    var d=map.distance(ll,pt), segLen=map.distance(a,b);
    if(d<best.d)best={d:d,seg:i,t:t,pt:pt,along:cumulative+segLen*t};
    cumulative+=segLen;
  }
  best.total=cumulative;
  return best;
}
function stopCandidates(name){
  return STOPS_DATA.filter(function(s){return String(s.name)===String(name);});
}
function commonRouteIds(a,b){
  var A={};a.forEach(function(s){A[String(s.route_id)]=true;});
  return b.map(function(s){return String(s.route_id);}).filter(function(id,i,arr){return A[id]&&arr.indexOf(id)===i;});
}
var recommendationLayer=L.layerGroup().addTo(map);
function populateStopDropdowns(){
  var inputs=[['originInput','originResults'],['destinationInput','destinationResults']];
  inputs.forEach(function(pair){
    var input=document.getElementById(pair[0]),results=document.getElementById(pair[1]); if(!input||!results)return;
    input._selectedStop=null;
    function render(q){
      q=String(q||'').trim().toLowerCase();
      var arr=STOPS_DATA.filter(function(s){var n=String(s.name||'');return n && (!q || n.toLowerCase().indexOf(q)>=0);})
        .sort(function(a,b){return String(a.name).localeCompare(String(b.name))||String(a.route_id).localeCompare(String(b.route_id));}).slice(0,100);
      results.innerHTML=arr.map(function(s,i){
        var idx=STOPS_DATA.indexOf(s);
        return '<button type="button" class="stop-search-option" data-index="'+idx+'"><b>'+safe(s.name)+'</b><small>Route '+safe(s.route_id||'—')+' · '+Number(s.lat).toFixed(4)+', '+Number(s.lng).toFixed(4)+'</small></button>';
      }).join('')||'<div class="stop-search-option empty">No matching stops</div>';
      results.classList.add('open');
      results.querySelectorAll('.stop-search-option[data-index]').forEach(function(el){el.onclick=function(){var s=STOPS_DATA[Number(el.dataset.index)];input.value=s.name;input._selectedStop=s;results.classList.remove('open');highlightRecommendationInputs();map.setView([s.lat,s.lng],Math.max(15,map.getZoom()));};});
    }
    input.addEventListener('focus',function(){render(input.value);});
    input.addEventListener('input',function(){input._selectedStop=null;render(input.value);recommendationLayer.clearLayers();});
    input.addEventListener('keydown',function(e){if(e.key==='ArrowDown'){var first=results.querySelector('.stop-search-option[data-index]');if(first){e.preventDefault();first.focus();}}if(e.key==='Enter'){var first=results.querySelector('.stop-search-option[data-index]');if(first){e.preventDefault();first.click();}}});
    document.addEventListener('click',function(e){if(!input.contains(e.target)&&!results.contains(e.target))results.classList.remove('open');});
  });
}
function highlightRecommendationInputs(){
  recommendationLayer.clearLayers();
  var o=document.getElementById('originInput')._selectedStop,d=document.getElementById('destinationInput')._selectedStop;
  if(o){L.circleMarker([o.lat,o.lng],{radius:10,color:'#fff',weight:3,fillColor:'#16a34a',fillOpacity:1,zIndexOffset:2000}).bindTooltip('Origin: '+o.name,{permanent:true,direction:'top',className:'recommend-origin-label'}).addTo(recommendationLayer);}
  if(d){L.circleMarker([d.lat,d.lng],{radius:10,color:'#fff',weight:3,fillColor:'#dc2626',fillOpacity:1,zIndexOffset:2000}).bindTooltip('Destination: '+d.name,{permanent:true,direction:'top',className:'recommend-destination-label'}).addTo(recommendationLayer);}
}
function stopCandidates(name){return STOPS_DATA.filter(function(s){return String(s.name)===String(name);});}
function commonRouteIds(a,b){var A={};a.forEach(function(s){A[String(s.route_id)]=true;});return b.map(function(s){return String(s.route_id);}).filter(function(id,i,arr){return A[id]&&arr.indexOf(id)===i;});}
function stopToStopMetrics(f,o,d){
  var coords=routeGeometryCoords(f); if(coords.length<2)return null;
  var op=projectPointOnRoute(coords,L.latLng(o.lat,o.lng)),dp=projectPointOnRoute(coords,L.latLng(d.lat,d.lng));
  if(!op.pt||!dp.pt)return null;
  return {distanceKm:Math.abs(dp.along-op.along)/1000,originPos:op.along,destinationPos:dp.along,totalMeters:op.total};
}
function recommend(){
  var oi=document.getElementById('originInput'),di=document.getElementById('destinationInput'),oName=oi.value.trim(),dName=di.value.trim(),box=document.getElementById('recommendation');
  if(!oi._selectedStop||!di._selectedStop||!oName||!dName||oName===dName){box.classList.remove('show');setStatus('Choose an Origin and Destination from the stop search lists.');return;}
  var origins=stopCandidates(oName),destinations=stopCandidates(dName),ids=commonRouteIds(origins,destinations),candidates=[];
  ids.forEach(function(rid){var f=ROUTES_DATA.features.find(function(x){return String(x.properties.Route_ID)===rid;});if(!f)return;origins.filter(function(s){return String(s.route_id)===rid;}).forEach(function(o){destinations.filter(function(s){return String(s.route_id)===rid;}).forEach(function(d){var m=stopToStopMetrics(f,o,d);if(m&&m.distanceKm>0)candidates.push({f:f,o:o,d:d,m:m});});});});
  if(!candidates.length){box.classList.add('show');box.innerHTML='<div class="rec-title">No direct route found</div><div class="rec-muted">No existing GeoJSON route serves both selected stops.</div>';setStatus('No direct route found between the selected stops.');highlightRecommendationInputs();return;}
  candidates.sort(function(a,b){return a.m.distanceKm-b.m.distanceKm;});
  var best=candidates[0],f=best.f,p=f.properties,km=best.m.distanceKm,fullKm=Number(p.Length)||best.m.totalMeters/1000,fullTime=Number(p['Travel Tim']);
  if(!isFinite(fullTime)||fullTime<=0)fullTime=fullKm/20*60;
  var time=fullKm>0?fullTime*(km/fullKm):(km/20*60),fare=fareForKm(km);
  clearSelection();selectedLayer=routeLayerById[p.Route_ID];selectedRoutes=[f];selectedLayer.setStyle(selectedStyle());selectedLayer.bringToFront();highlightRecommendationInputs();
  map.fitBounds(selectedLayer.getBounds(),{paddingTopLeft:[320,40],paddingBottomRight:[360,120]});renderRouteDetail(f);
  box.classList.add('show');box.innerHTML='<div class="rec-title">Recommended Route <span>'+safe(p.Route_ID)+'</span></div><div class="rec-row"><b>Bus name</b><span>'+safe(p.Operator||'—')+'</span></div><div class="rec-row"><b>Origin</b><span>'+safe(oName)+'</span></div><div class="rec-row"><b>Destination</b><span>'+safe(dName)+'</span></div><div class="rec-grid"><div><b>Approx. Distance</b><span>'+km.toFixed(1)+' km</span></div><div><b>Approx. Time</b><span>'+Math.round(time)+' min</span></div><div><b>Approx. Fare</b><span>BDT '+fare.toLocaleString()+'</span></div></div><div class="rec-note">Distance is measured along the selected route between the two official stops. Fare: BDT 2.53/km; minimum BDT 10; rounded upward to the nearest BDT 5.</div>';
  setStatus('Recommended route: '+p.Route_ID+'.');updateJpegButton();
}
document.getElementById('recommendBtn').onclick=recommend;

/* JPEG export: dedicated export map so only requested features are rendered at correct positions */
function updateJpegButton(){
  var b=document.getElementById('jpegExportBtn');
  if(b){b.disabled=!selectedRoutes.length;b.title=selectedRoutes.length?'Export selected route, its labelled stops and temporary drawings as JPEG':'Select a route first';}
}
function ensureExportMap(){
  var el=document.getElementById('exportMapCanvas');
  if(el) return el;
  el=document.createElement('div');
  el.id='exportMapCanvas';
  el.style.cssText='position:fixed;left:-20000px;top:0;width:1600px;height:900px;background:#eef2f5;z-index:-1;overflow:hidden;';
  document.body.appendChild(el);
  return el;
}
function exportStopLabel(s, cls){
  return L.marker([s.lat,s.lng],{icon:L.divIcon({className:cls||'export-stop-label',html:'<span>'+safe(s.name)+'</span>',iconSize:[1,1],iconAnchor:[0,0]}),interactive:false});
}
function drawExportLegend(x,mx,my){
  var bx=mx+30,by=my+30;
  x.fillStyle='rgba(255,255,255,.97)';x.fillRect(bx,by,390,150);x.strokeStyle='#b8c3d1';x.lineWidth=2;x.strokeRect(bx,by,390,150);
  x.fillStyle='#122240';x.font='700 22px Arial';x.fillText('Legend',bx+20,by+32);
  x.strokeStyle='#E4572E';x.lineWidth=7;x.beginPath();x.moveTo(bx+20,by+58);x.lineTo(bx+65,by+58);x.stroke();
  x.fillStyle='#17243a';x.font='16px Arial';x.fillText('Selected route',bx+82,by+64);
  x.fillStyle='#122240';x.beginPath();x.arc(bx+42,by+87,7,0,Math.PI*2);x.fill();x.fillStyle='#17243a';x.fillText('Official bus stop',bx+82,by+93);
  x.strokeStyle='#7c3aed';x.lineWidth=7;x.setLineDash([12,7]);x.beginPath();x.moveTo(bx+20,by+116);x.lineTo(bx+65,by+116);x.stroke();x.setLineDash([]);x.fillStyle='#17243a';x.fillText('Temporary route',bx+82,by+122);
  x.fillStyle='#7c3aed';x.beginPath();x.arc(bx+42,by+143,7,0,Math.PI*2);x.fill();x.fillStyle='#17243a';x.fillText('Temporary stop',bx+82,by+149);
}
function drawExportNorthScale(x,mx,my,mw,mh,mapObj){
  var nx=mx+mw-100,ny=my+75;x.fillStyle='#122240';x.font='700 34px Arial';x.textAlign='center';x.fillText('N',nx,ny);x.beginPath();x.moveTo(nx,ny+12);x.lineTo(nx-15,ny+42);x.lineTo(nx,ny+34);x.lineTo(nx+15,ny+42);x.closePath();x.fill();x.strokeStyle='#122240';x.lineWidth=5;x.beginPath();x.moveTo(nx,ny+34);x.lineTo(nx,ny+92);x.stroke();x.textAlign='left';
  var lat=mapObj.getCenter().lat,metersPerPx=156543.03392*Math.cos(lat*Math.PI/180)/Math.pow(2,mapObj.getZoom()),target=2000,px=target/metersPerPx;while(px>260){target/=2;px=target/metersPerPx;}while(px<110){target*=2;px=target/metersPerPx;}var sx=mx+mw-310,sy=my+mh-35;x.strokeStyle='#17243a';x.lineWidth=6;x.beginPath();x.moveTo(sx,sy);x.lineTo(sx+px,sy);x.stroke();x.lineWidth=2;x.beginPath();x.moveTo(sx,sy-10);x.lineTo(sx,sy+10);x.moveTo(sx+px,sy-10);x.lineTo(sx+px,sy+10);x.stroke();x.fillStyle='#17243a';x.font='700 17px Arial';x.fillText(target>=1000?(target/1000)+' km':target+' m',sx,sy-18);
}
async function waitForExportTiles(mapObj, timeout){
  var tiles=Array.from(document.querySelectorAll('#exportMapCanvas img.leaflet-tile'));
  var start=Date.now();
  while(Date.now()-start<timeout){
    tiles=Array.from(document.querySelectorAll('#exportMapCanvas img.leaflet-tile'));
    if(tiles.length && tiles.every(function(im){return im.complete && im.naturalWidth>0;})) return;
    await new Promise(function(r){setTimeout(r,180);});
  }
}
async function exportJPEG(){
  if(!selectedRoutes.length){setStatus('Select a route first; only the selected route and temporary drawings can be exported.');return;}
  var W=1800,H=1200,margin=70,head=105,foot=55,mx=margin,my=head+25,mw=W-2*margin,mh=H-head-foot-55;
  var exportEl=ensureExportMap(),exportMap=null,group=null,cleanup=[];
  try{
    exportMap=L.map(exportEl,{zoomControl:false,attributionControl:false,preferCanvas:false,fadeAnimation:false,zoomAnimation:false});
    var base=L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{subdomains:'abcd',maxZoom:20,crossOrigin:'anonymous'}).addTo(exportMap);cleanup.push(function(){exportMap.removeLayer(base);});
    group=L.layerGroup().addTo(exportMap);
    var bounds=L.latLngBounds([]);
    selectedRoutes.forEach(function(f){
      var line=L.geoJSON(f,{style:{color:'#E4572E',weight:7,opacity:.98}}).addTo(group);bounds.extend(line.getBounds());
      routeStops(f).forEach(function(s){L.circleMarker([s.lat,s.lng],{radius:7,color:'#fff',weight:2,fillColor:'#122240',fillOpacity:1}).addTo(group);exportStopLabel(s).addTo(group);bounds.extend([s.lat,s.lng]);});
    });
    tempRoutes.forEach(function(r){L.polyline(r.latlngs,{color:'#7c3aed',weight:7,dashArray:'12 7',opacity:.98}).addTo(group);r.latlngs.forEach(function(ll){bounds.extend(ll);});});
    tempPoints.forEach(function(p){L.circleMarker([p.lat,p.lng],{radius:9,color:'#fff',weight:2,fillColor:'#7c3aed',fillOpacity:1}).addTo(group);exportStopLabel(p,'export-stop-label temp-export-label').addTo(group);bounds.extend([p.lat,p.lng]);});
    if(bounds.isValid())exportMap.fitBounds(bounds,{padding:[90,110],maxZoom:15});
    exportMap.invalidateSize(true);
    await new Promise(function(r){setTimeout(r,500);});
    await waitForExportTiles(exportMap,8000);
    var mapCanvas=await html2canvas(exportEl,{useCORS:true,allowTaint:false,backgroundColor:'#eef2f5',scale:1,logging:false,removeContainer:true});
    var c=document.createElement('canvas');c.width=W;c.height=H;var x=c.getContext('2d');x.fillStyle='#f3f5f7';x.fillRect(0,0,W,H);x.fillStyle='#122240';x.fillRect(0,0,W,head);x.fillStyle='#fff';x.font='700 30px Arial';x.fillText('DTCA Bus Route Rationalization Project',margin,43);x.font='500 17px Arial';x.fillStyle='#dbe7f5';x.fillText('Selected Route Map · Official Stops & Temporary User Drawings',margin,75);x.drawImage(mapCanvas,0,0,mapCanvas.width,mapCanvas.height,mx,my,mw,mh);x.strokeStyle='#9aa8b8';x.lineWidth=2;x.strokeRect(mx,my,mw,mh);drawExportLegend(x,mx,my);drawExportNorthScale(x,mx,my,mw,mh,exportMap);x.fillStyle='#334155';x.font='14px Arial';x.fillText('Basemap: © OpenStreetMap contributors © CARTO',margin,H-34);x.fillText('Source: DTCA BRR Project',margin,H-16);x.textAlign='right';x.fillText(new Date().toLocaleDateString(),W-margin,H-16);x.textAlign='left';
    var a=document.createElement('a');a.download='DTCA_selected_route_map.jpg';a.href=c.toDataURL('image/jpeg',.95);document.body.appendChild(a);a.click();a.remove();setStatus('JPEG exported with correctly aligned basemap, selected route, its labelled stops and temporary drawings.');
  }catch(err){setStatus('JPEG export failed: '+err.message);}
  finally{if(exportMap){exportMap.remove();}if(exportEl.parentNode)exportEl.parentNode.removeChild(exportEl);}
}
document.getElementById('jpegExportBtn').onclick=exportJPEG;
populateStopDropdowns();

/* Remove legacy export/edit controls if present in older HTML */
['importKmlBtn','exportKmlBtn','exportCsvBtn','saveProjectBtn','loadProjectBtn','resetProjectBtn'].forEach(function(id){var e=document.getElementById(id);if(e){e.disabled=true;e.style.display='none';}});

/* Stats */
var total=0,ac=0;ROUTES_DATA.features.forEach(function(f){total+=Number(f.properties.Length)||0;if(isAC(f.properties))ac++;});document.getElementById('statRoutes').textContent=ROUTES_DATA.features.length;document.getElementById('statStops').textContent=STOPS_DATA.length.toLocaleString();document.getElementById('statLength').textContent=Math.round(total).toLocaleString();document.getElementById('statAC').textContent=ac;document.getElementById('hdrRoutes').textContent=ROUTES_DATA.features.length;document.getElementById('hdrStops').textContent=STOPS_DATA.length.toLocaleString();updateTable();updateJpegButton();

})();
