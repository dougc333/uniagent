const features = [
  ["⚡", "Fast setup", "Launch your workspace in just a few minutes."],
  ["✓", "Clear tasks", "Keep ownership and priorities visible."],
  ["↗", "Live reports", "Understand progress with simple reporting."],
];

export default function App() {
  return (
    <main className="features">
      <h1>Everything you need</h1>
      <p className="subtitle">Simple tools for productive teams.</p>
      <section className="card-grid">
        {features.map(([icon, title, description]) => (
          <article className="card" key={title}>
            <div className="icon">{icon}</div>
            <h2>{title}</h2>
            <p>{description}</p>
          </article>
        ))}
      </section>
    </main>
  );
}
