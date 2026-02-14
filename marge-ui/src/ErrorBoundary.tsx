import { Component, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      const btnStyle = {
        padding: '0.5rem 1rem',
        background: '#333',
        color: '#fff',
        border: '1px solid #555',
        borderRadius: '6px',
        cursor: 'pointer',
        marginRight: '0.5rem',
      } as const;
      return (
        <div style={{ padding: '2rem', color: '#e55', textAlign: 'center' }}>
          <h2>Dashboard Error</h2>
          <p>{this.state.error?.message}</p>
          <div style={{ marginTop: '1rem' }}>
            <button onClick={() => this.setState({ hasError: false })} style={btnStyle}>
              Retry
            </button>
            <button onClick={() => window.location.reload()} style={btnStyle}>
              Reload Page
            </button>
          </div>
          {import.meta.env.DEV && this.state.error?.stack && (
            <pre style={{
              marginTop: '1rem',
              textAlign: 'left',
              fontSize: '0.75rem',
              color: '#999',
              overflow: 'auto',
              maxHeight: '200px',
              padding: '1rem',
              background: '#1a1a1a',
              borderRadius: '6px',
            }}>
              {this.state.error.stack}
            </pre>
          )}
        </div>
      );
    }
    return this.props.children;
  }
}
