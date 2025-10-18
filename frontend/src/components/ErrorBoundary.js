import React from 'react';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    this.setState({
      error: error,
      errorInfo: errorInfo
    });
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
          <div className="max-w-xl w-full space-y-8 bg-white p-8 rounded-xl shadow-sm border border-gray-200">
            <div>
              <h2 className="text-2xl font-bold text-gray-900 mb-4">Une erreur est survenue</h2>
              <p className="text-gray-600 mb-6">
                L'application a rencontré une erreur inattendue. Essayez de recharger la page.
              </p>
              <button
                onClick={() => window.location.reload()}
                className="bg-sky-600 hover:bg-sky-700 text-white font-semibold py-2 px-4 rounded-lg transition-colors"
              >
                Recharger l'application
              </button>
            </div>
            {process.env.NODE_ENV === 'development' && (
              <div className="mt-6 p-4 bg-gray-100 rounded-lg">
                <p className="font-mono text-sm text-red-600 whitespace-pre-wrap">
                  {this.state.error && this.state.error.toString()}
                </p>
              </div>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}