export default function EventsPage() {
  return (
    <div>
      <h1>Events Explorer</h1>
      <p>Filtre server-side + Evidence Drawer pentru linia raw.</p>
      <table className="table">
        <thead>
          <tr>
            <th>Time</th>
            <th>Type</th>
            <th>Src</th>
            <th>Dst</th>
            <th>Amount</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>-</td>
            <td>PHONE_TRANSFER</td>
            <td>123</td>
            <td>456</td>
            <td>637000$</td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}
