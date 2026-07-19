export default function App() {
  return (
    <main className="stage">
      <section className="panel">
        <h1>Welcome back</h1>
        <p className="subtitle">Sign in to continue to your account.</p>
        <form>
          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input id="email" type="email" placeholder="you@example.com" />
          </div>
          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input id="password" type="password" placeholder="••••••••" />
          </div>
          <button type="submit">Sign in</button>
        </form>
        <p className="help">Need an account? <a href="#">Create one</a></p>
      </section>
    </main>
  );
}
