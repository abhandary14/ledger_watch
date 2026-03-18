import { Component, type ErrorInfo, type ReactNode } from 'react'
import { Button } from '@/components/ui/button'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false }

  static getDerivedStateFromError(): State {
    return { hasError: true }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('ErrorBoundary caught:', error, info.componentStack)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex h-full min-h-[400px] flex-col items-center justify-center gap-4 text-center">
          <div className="text-4xl">⚠</div>
          <h2 className="text-lg font-semibold">Something went wrong</h2>
          <p className="text-sm text-muted-foreground">
            An unexpected error occurred. Try refreshing the page.
          </p>
          <Button
            variant="outline"
            onClick={() => {
              this.setState({ hasError: false })
              window.location.reload()
            }}
          >
            Retry
          </Button>
        </div>
      )
    }

    return this.props.children
  }
}
