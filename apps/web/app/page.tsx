export default function DashboardPage() {
  return (
    <div>
      <h1>Phoenix Investigation Panel V2</h1>
      <p>Dashboard overview pentru ingest, evenimente si fluxuri.</p>
      <div className="card-grid">
        <div className="card">
          <div className="badge">Imports</div>
          <h3>0 fisiere procesate</h3>
          <p>Incarca transcripturi si porneste ingestul.</p>
        </div>
        <div className="card">
          <div className="badge">Events</div>
          <h3>0 events</h3>
          <p>Explorare, filtre, drill-down pe evidence.</p>
        </div>
        <div className="card">
          <div className="badge">Report Packs</div>
          <h3>0 packs</h3>
          <p>Genereaza zip-uri cu dovezi si CSV.</p>
        </div>
      </div>
    </div>
  );
}
