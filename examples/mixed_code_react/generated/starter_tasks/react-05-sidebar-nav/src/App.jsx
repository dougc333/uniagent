export default function App() {
  return (
    <aside className="sidebar">
      <div className="logo">Orbit</div>
      <nav aria-label="Workspace">
        <a className="active" href="#">Overview</a>
        <a href="#">Projects</a>
        <a href="#">Calendar</a>
        <a href="#">Settings</a>
      </nav>
      <div className="user">
        <span className="avatar">AR</span>
        <span><strong>Alex Reed</strong><small>Admin</small></span>
      </div>
    </aside>
  );
}
