
FloodLens

Main



Your message
Build the frontend for FloodLens, a flood early-warning and food-price impact dashboard for Pakistan. It helps disaster responders and analysts see where floods are likely in the next 7 days, who is exposed, and how floods will push up food prices in nearby markets.

This is a UI-only build with mock data. Use React, TypeScript, Tailwind CSS, shadcn/ui, react-leaflet with OpenStreetMap tiles (with attribution, no API keys) and Recharts. No backend, no auth, no API calls. Put all data in one mock-data file using the types below, and keep components presentational with typed props, so real data can be wired in later.

Design: a professional situation room

Style reference: modern operations dashboards such as Linear, Vercel and Windy.com. Calm and dense with information. Not a marketing template.
Dark mode by default for the situation room, plus a finished light mode.
Neutral greys for the interface. Colour is reserved for data.
Risk levels use a colour-blind-safe sequential scale: low (pale yellow), moderate (amber), high (orange), severe (deep magenta). Never rely on red versus green alone.
Inter for text, tabular figures for numbers. Clear type scale: page titles 24px, section titles 16px, body 14px, labels 12px in muted grey.
8px spacing grid, subtle 1px borders, small radii, Lucide icons at 16px.
Skeleton loaders, empty states with one clear action, and error states with a retry button.
No emojis, stock illustrations or decorative charts.
Layout of the main screen, the Situation Room

Top bar: "FloodLens" logo text, a "Live, updated 2 min ago" indicator, navigation (Situation Room, Food Prices, Sources & Methods), and a light/dark toggle.
Under the top bar: a time slider from 7 days ago, through now, to 7 days ahead, with a play button. Clearly label observed versus forecast. Moving it updates the map, KPIs and alerts.
A slim KPI row: districts at high or severe risk, people exposed, river gauges above high flood level, and markets with a forecast price spike.
Centre: a full-height map of Pakistan.
Left panel, collapsible: layer toggles in three groups, each with a legend, an opacity slider and a small "source, last updated" line:
Hazard: flood risk forecast by district, river gauges and barrages, rainfall (last 24 hours or next 72 hours), satellite flood extent
Exposure: population, cropland
Impact: food-price forecast by market
Right panel, collapsible: the alerts feed, sorted by severity (Watch, Warning, Emergency). Each alert shows the place, river or district, time, and a one-line reason. Clicking it zooms the map and opens the district drawer.
District drawer (opens over the right panel)

Risk level now and over the next 7 days, as a small trend chart
What's driving the risk: rainfall forecast, nearest river level against its flood thresholds, recent rain
Nearest gauges with mini hydrographs, showing threshold lines for low, medium, high, very high and exceptionally high flood levels
Exposure: population and cropland affected
Food prices in nearby markets: current against predicted prices for wheat flour, rice, tomatoes, onions and pulses, with a confidence band
Sources used, each with its last-updated time
Food Prices page

A table of markets: commodity, current price in PKR, predicted change over the next 2 to 4 weeks, confidence, and a "flood-linked" badge when the forecast is driven by flood risk upstream
Selecting a market shows a price chart with history, the forecast and its confidence band, plus a short "why" line
A small map of markets coloured by forecast change
Sources & Methods page

A table of data sources: name, what it provides, update frequency, last updated, and a link
Short sections on how the flood risk model and the price model work, with their accuracy figures and known limits
Mobile On phones, use tabs for Map, Alerts and Layers. Alerts first.

Mock data Use realistic Pakistani places, roughly 10 districts and 8 gauges:

Districts such as Dadu, Jacobabad, Larkana, Rajanpur, Dera Ghazi Khan, Swat, Nowshera, Charsadda
Rivers: Indus, Jhelum, Chenab, Kabul, Swat
Gauges and barrages such as Tarbela, Chashma, Taunsa, Guddu, Sukkur, Kotri, Marala
River flow in cusecs, prices in PKR
Use simplified polygons for districts; I'll replace them with a real boundary GeoJSON later
Types type RiskLevel = "low" | "moderate" | "high" | "severe"; type District = { id: string; name: string; province: string; centroid: [number, number]; polygon: [number, number][]; risk: RiskLevel; riskForecast: { date: string; risk: RiskLevel }[]; population: number; exposedPopulation: number; croplandHa: number; drivers: string[] }; type Gauge = { id: string; name: string; river: string; location: [number, number]; flowCusecs: number; thresholds: { low: number; medium: number; high: number; veryHigh: number; exceptionallyHigh: number }; series: { date: string; flowCusecs: number; forecast: boolean }[] }; type Alert = { id: string; severity: "watch" | "warning" | "emergency"; title: string; reason: string; districtId: string; issuedAt: string }; type Market = { id: string; name: string; location: [number, number]; prices: PriceSeries[] }; type PriceSeries = { commodity: string; unit: string; current: number; history: { date: string; price: number }[]; forecast: { date: string; price: number; low: number; high: number }[]; floodLinked: boolean; reason: string }; type Source = { id: string; name: string; provides: string; updateFrequency: string; lastUpdated: string; url: string };

Show more
6 hours ago

Base44 response
I'll build FloodLens as a dense, dark-first situation room. Let me check the project scaffolding first.


Inspecting project scaffolding
Base44 response
Building FloodLens now — I'll start with the data layer, theme tokens and foundation, then the situation room.


Built the index, types, and 4 more
Base44 response
Foundation is in. Now the mock dataset and derived-data helpers.


Built the styles and mock Data
Base44 response

Updated the mock Data and select
Base44 response
Now the interface layer — chrome, panels, map and drawer.


Updated the risk, Tag, and 5 more
Base44 response

Built the layer Config, Risk Scale Legend, and 5 more
Base44 response

Built the Map View, Map Legend, and 3 more
Base44 response

Updated the Map View, layers, and 4 more
Base44 response

Updated the Map View, Layer Row, and 2 more
Base44 response

Built the layers
Base44 response

Built the Alert Item, Alerts Panel, and 2 more
Base44 response

Updated the Gauge Hydrograph, Risk Drivers, and 5 more
Base44 response

Updated the layers, Map View, and 3 more
Base44 response

Built the Layer Row and Layer Group Legend
Base44 response

Updated the Map View, Layers Panel, and Situation Room
Base44 response

Checking the map layer code
Base44 response

Updated the Map View and Map Legend
Base44 response

Updated the Map View

Verified the app — Opening the situation room for a first look
Base44 response

Updated select
Base44 response

Thought for 2s

Verified the app — Checking the situation room renders
Base44 response
The situation room renders. Fixing the map tiles (Carto needs a key), then building the remaining two pages.


Updated the Map View, Base Tiles, and 4 more
Base44 response

Updated the Map View, Market Price Rows, and 10 more
Base44 response

Updated the Market Price Table
Base44 response

Updated the Food Prices
Base44 response

Thought for 5s

Verified the app — Checking the timeline updates the map and alerts
Base44 response

Thought for 5s

Verified the app — Testing the drawer, layer feed and playback
Base44 response

Thought for 7s

Verified the app — Checking the food, sources and mobile views
Base44 response

Thought for 8s

Verified the app — Re-checking light mode and mobile tabs
Base44 response

Thought for 8s
FloodLens is built and verified end to end.

<next_prompt>Add a ranked district list view for triage without the map</next_prompt>

What's there

Situation Room — timeline from −7 days to +7 days with playback and an observed/forecast marker, four KPI tiles, full-height OpenStreetMap view (no API key; darkened in dark mode), collapsible layers panel (hazard / exposure / impact with legends, opacity sliders and source lines) and a collapsible alerts feed sorted by severity.
District drawer — seven-day risk trend, what's driving the risk, nearest gauges with hydrographs showing all five flood-level threshold lines, exposure, four-week prices in nearby markets with confidence bands, and the sources used.
Food Prices — 40 market × commodity series with 2-week and 4-week changes, confidence and flood-linked badges, plus a market map and a price chart with history, forecast and the 80% band.
Sources & Methods — nine feeds with update frequency and last-updated times, and both models with accuracy figures and known limits.
Dark by default with a finished light mode; everything reads from one mock data file using your exact types, and components take typed props so real data can drop in.
Verified in the live preview

Timeline moves KPIs, map shading and alerts (5 → 1 districts at risk at +7 days); alerts empty state and its "Jump to now" action; alert → zoom → drawer (all six sections, three charts, threshold lines); collapse/expand both panels; play/pause; satellite layer error state with a working Retry; all three routes; table filters and row selection changing the chart; source register and limits; light and dark modes (checked computed styles, not just pixels); mobile tabs with Alerts first and no sideways scroll; no console errors.
Not automatically driven, worth a quick look by hand: hovering map markers for their tooltips, clicking a district shape directly (I drove the alert path instead), and dragging the opacity sliders.
Two honest notes: the district outlines are simplified placeholders ready to swap for your real GeoJSON, and the satellite feed's error/retry is a mock state so the failure design is visible.

6 hours ago




Suggestions


What do you want to change?



Auto
Build







30% off
Publish
https://flood-lens-pakistan.base44.app

Connect domain


Back to Dashboard
Code files


base44
src
api
components
common
EmptyState.tsx
ErrorState.tsx
Panel.tsx
SkeletonBlock.tsx
SourceLine.tsx
Tag.tsx
food
MarketPriceTable.tsx
MarketsMap.tsx
PriceForecastChart.tsx
layout
map
situation
AlertItem.tsx
AlertsPanel.tsx
DistrictDrawer.tsx
ExposureStats.tsx
FloodLevelLegend.tsx
GaugeHydrograph.tsx
LayerGroupLegend.tsx
LayerRow.tsx
layers.ts
LayersPanel.tsx
MapLegend.tsx
MapView.tsx
MarkerLegend.tsx
MarketPriceRows.tsx
RiskDrivers.tsx
RiskScaleLegend.tsx
RiskTrendChart.tsx
ui
accordion.jsx
alert-dialog.jsx
alert.jsx
aspect-ratio.jsx
avatar.jsx
badge.jsx
breadcrumb.jsx
button.jsx
calendar.jsx
card.jsx
carousel.jsx
chart.jsx
checkbox.jsx
collapsible.jsx
command.jsx
context-menu.jsx
dialog.jsx
drawer.jsx
dropdown-menu.jsx
form.jsx
hover-card.jsx
image-helpers.js
image.jsx
input-otp.jsx
input.jsx
label.jsx
menubar.jsx
navigation-menu.jsx
pagination.jsx
popover.jsx
progress.jsx
radio-group.jsx
resizable.jsx
responsive-image.jsx
scroll-area.jsx
select.jsx
separator.jsx
sheet.jsx
sidebar.jsx
skeleton.jsx
slider.jsx
sonner.jsx
switch.jsx
table.jsx
tabs.jsx
textarea.jsx
toast.jsx
toaster.jsx
toggle-group.jsx
toggle.jsx
tooltip.jsx
use-responsive-image.jsx
use-toast.jsx
AuthLayout.jsx
GoogleIcon.jsx
ProtectedRoute.jsx
ScrollToTop.jsx
UserNotRegisteredError.jsx
data
hooks
lib
pages
utils
App.jsx
index.css
main.jsx
.gitignore
AGENTS.md
CLAUDE.md
components.json
eslint.config.js
index.html
jsconfig.json
package.json
postcss.config.js
README.md
tailwind.config.js
vite.config.js
src
components
ui
input.jsx

Split view
Code editing is only available on paid plans.

View plans
