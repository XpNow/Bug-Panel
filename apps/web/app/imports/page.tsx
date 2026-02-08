export default function ImportsPage() {
  return (
    <div>
      <h1>Imports</h1>
      <p>Upload transcripturi mari si porneste ingest-ul direct din UI.</p>
      <div className="section card">
        <h3>Upload</h3>
        <p>Endpoint-uri: POST /uploads/create, PUT /uploads/{'{id}'}/chunk, POST /uploads/{'{id}'}/finalize.</p>
      </div>
      <div className="section card">
        <h3>Ingest Jobs</h3>
        <p>Monitorizeaza progresul live si vezi preview-ul eventurilor.</p>
      </div>
    </div>
  );
}
