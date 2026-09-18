import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import {
  clearAccessToken,
  getAccessToken,
  getCurrentUser,
  loginUser,
  registerUser,
} from './lib/api';
import type { User } from './types/auth';
import './App.css';

type AuthMode = 'login' | 'register';

function App() {
  const [mode, setMode] = useState<AuthMode>('login');
  const [user, setUser] = useState<User | null>(null);
  const [checkingSession, setCheckingSession] = useState(true);

  useEffect(() => {
    const restoreSession = async () => {
      if (!getAccessToken()) {
        setCheckingSession(false);
        return;
      }

      try {
        const currentUser = await getCurrentUser();
        setUser(currentUser);
      } catch {
        clearAccessToken();
      } finally {
        setCheckingSession(false);
      }
    };

    void restoreSession();
  }, []);

  if (checkingSession) {
    return (
      <main className="auth-shell">
        <div className="loading-screen">
          <div className="brand-mark">आ</div>
          <p>Restoring secure session...</p>
        </div>
      </main>
    );
  }

  if (user) {
    return (
      <main className="app-shell">
        <header className="app-header">
          <div className="brand">
            <div className="brand-mark brand-mark-small">आ</div>
            <div>
              <strong>AAKAR</strong>
              <span>आकार</span>
            </div>
          </div>

          <button
            type="button"
            className="ghost-button"
            onClick={() => {
              clearAccessToken();
              setUser(null);
            }}
          >
            Sign out
          </button>
        </header>

        <section className="session-card">
          <div className="status-badge">
            <span className="status-dot" />
            Authenticated session
          </div>

          <h1>Welcome, {user.full_name}</h1>

          <p className="session-copy">
            Your AAKAR account is authenticated and the current session token
            has been verified by the backend.
          </p>

          <div className="profile-grid">
            <div className="profile-item">
              <span>Email</span>
              <strong>{user.email}</strong>
            </div>

            <div className="profile-item">
              <span>Account status</span>
              <strong>{user.is_active ? 'Active' : 'Inactive'}</strong>
            </div>

            <div className="profile-item">
              <span>Email verification</span>
              <strong>
                {user.is_email_verified ? 'Verified' : 'Not verified'}
              </strong>
            </div>

            <div className="profile-item">
              <span>Authentication</span>
              <strong>JWT Bearer</strong>
            </div>
          </div>

          <div className="next-module-note">
            <span>AAKAR</span>
            Authorized modules will become available as role and permission
            controls are added.
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="auth-shell">
      <section className="auth-visual">
        <div className="contour contour-one" />
        <div className="contour contour-two" />
        <div className="contour contour-three" />

        <div className="visual-content">
          <div className="brand">
            <div className="brand-mark">आ</div>
            <div>
              <strong>AAKAR</strong>
              <span>आकार</span>
            </div>
          </div>

          <div className="visual-copy">
            <p className="eyebrow">NATIONAL LAND MANAGEMENT SYSTEM</p>
            <h1>Shaping land.<br />Empowering development.</h1>
            <p>
              Secure access to the AAKAR platform for digital land acquisition
              workflows, records, and operational monitoring.
            </p>
          </div>

          <div className="visual-footer">
            <span>Secure government access</span>
            <span>AAKAR v0.1</span>
          </div>
        </div>
      </section>

      <section className="auth-panel">
        <div className="auth-card">
          <div className="mobile-brand">
            <div className="brand-mark">आ</div>
            <div>
              <strong>AAKAR</strong>
              <span>आकार</span>
            </div>
          </div>

          {mode === 'login' ? (
            <LoginForm
              onAuthenticated={setUser}
              onSwitchToRegister={() => setMode('register')}
            />
          ) : (
            <RegisterForm
              onRegistered={() => setMode('login')}
              onSwitchToLogin={() => setMode('login')}
            />
          )}
        </div>
      </section>
    </main>
  );
}

interface LoginFormProps {
  onAuthenticated: (user: User) => void;
  onSwitchToRegister: () => void;
}

function LoginForm({
  onAuthenticated,
  onSwitchToRegister,
}: LoginFormProps) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await loginUser({
        email,
        password,
      });

      onAuthenticated(response.user);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'Unable to sign in.',
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <div className="auth-heading">
        <p className="eyebrow">SECURE SIGN-IN</p>
        <h2>Welcome back</h2>
        <p>Sign in to access your AAKAR workspace.</p>
      </div>

      <form className="auth-form" onSubmit={handleSubmit}>
        <label htmlFor="login-email">
          Email address
          <input
            id="login-email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="name@department.gov.in"
            required
          />
        </label>

        <label htmlFor="login-password">
          Password
          <input
            id="login-password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="Enter your password"
            required
          />
        </label>

        {error && (
          <div className="error-message" role="alert">
            {error}
          </div>
        )}

        <button className="primary-button" type="submit" disabled={loading}>
          {loading ? 'Signing in...' : 'Sign in'}
        </button>
      </form>

      <p className="auth-switch">
        New to AAKAR?
        <button type="button" onClick={onSwitchToRegister}>
          Create an account
        </button>
      </p>
    </>
  );
}

interface RegisterFormProps {
  onRegistered: () => void;
  onSwitchToLogin: () => void;
}

function RegisterForm({
  onRegistered,
  onSwitchToLogin,
}: RegisterFormProps) {
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);

    try {
      await registerUser({
        full_name: fullName,
        email,
        password,
      });

      setFullName('');
      setEmail('');
      setPassword('');
      setSuccess('Account created successfully. You can now sign in.');
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'Unable to create the account.',
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <div className="auth-heading">
        <p className="eyebrow">ACCOUNT REGISTRATION</p>
        <h2>Create your account</h2>
        <p>Set up an AAKAR account for secure platform access.</p>
      </div>

      <form className="auth-form" onSubmit={handleSubmit}>
        <label htmlFor="register-name">
          Full name
          <input
            id="register-name"
            type="text"
            autoComplete="name"
            value={fullName}
            onChange={(event) => setFullName(event.target.value)}
            placeholder="Enter your full name"
            minLength={2}
            maxLength={150}
            required
          />
        </label>

        <label htmlFor="register-email">
          Email address
          <input
            id="register-email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="name@department.gov.in"
            required
          />
        </label>

        <label htmlFor="register-password">
          Password
          <input
            id="register-password"
            type="password"
            autoComplete="new-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="Minimum 8 characters"
            minLength={8}
            maxLength={128}
            required
          />
        </label>

        {error && (
          <div className="error-message" role="alert">
            {error}
          </div>
        )}

        {success && (
          <div className="success-message" role="status">
            {success}
          </div>
        )}

        <button className="primary-button" type="submit" disabled={loading}>
          {loading ? 'Creating account...' : 'Create account'}
        </button>
      </form>

      <p className="auth-switch">
        Already have an account?
        <button
          type="button"
          onClick={() => {
            onRegistered();
            setSuccess('');
            setError('');
          }}
        >
          Sign in
        </button>
      </p>

      <button
        type="button"
        className="back-button"
        onClick={onSwitchToLogin}
      >
        ← Back to sign in
      </button>
    </>
  );
}

export default App;