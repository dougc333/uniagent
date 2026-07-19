const stats = [
  ["Revenue", "$24,800", "+12.5%"],
  ["Orders", "1,429", "+8.2%"],
  ["Customers", "892", "+5.1%"],
];

export default function App() {
  return (
    <>
      <aside className="sidebar">
        <div className="logo">Pulse</div>
        <nav aria-label="Dashboard">
          <a className="active" href="#">Overview</a>
          <a href="#">Analytics</a>
          <a href="#">Customers</a>
          <a href="#">Settings</a>
        </nav>
      </aside>
      <main>
        <header>
          <div>
            <h1>Overview</h1>
            <p>Here is what is happening today.</p>
          </div>
          <div className="avatar">DC</div>
        </header>
        <section className="stats" aria-label="Statistics">
          {stats.map(([label, value, change]) => (
            <article key={label}><span>{label}</span><strong>{value}</strong><small>{change}</small></article>
          ))}
        </section>
        <section className="activity">
          <h2>Weekly activity</h2>
          {[88, 72, 60, 44].map((width) => (
            <div className="bar" key={width}><i style={{ width: `${width}%` }} /></div>
          ))}
        </section>
      </main>
    </>
  );
}
