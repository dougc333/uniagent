export default function App() {
  return (
    <footer>
      <div className="top-row">
        <a className="brand" href="#">Acme</a>
        <nav aria-label="Footer">
          <a href="#">Product</a>
          <a href="#">Company</a>
          <a href="#">Resources</a>
          <a href="#">Contact</a>
        </nav>
      </div>
      <div className="divider" />
      <div className="bottom-row">
        <small>© 2026 Acme, Inc. All rights reserved.</small>
        <div className="socials">
          <a href="#" aria-label="X">X</a>
          <a href="#" aria-label="LinkedIn">in</a>
          <a href="#" aria-label="GitHub">gh</a>
        </div>
      </div>
    </footer>
  );
}
