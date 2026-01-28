import "@testing-library/jest-dom/vitest";
import { server } from "./mocks/server";

// Mock EventSource (not available in jsdom)
class MockEventSource {
  static instances: MockEventSource[] = [];
  url: string;
  readyState = 0;
  onopen: ((event: Event) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  private listeners: Record<string, ((event: MessageEvent) => void)[]> = {};

  constructor(url: string) {
    this.url = url;
    this.readyState = 1;
    MockEventSource.instances.push(this);
    // Simulate async open
    queueMicrotask(() => {
      if (this.readyState === 1) {
        this.onopen?.(new Event("open"));
      }
    });
  }

  addEventListener(type: string, listener: (event: MessageEvent) => void) {
    this.listeners[type] = this.listeners[type] ?? [];
    this.listeners[type].push(listener);
  }

  removeEventListener(type: string, listener: (event: MessageEvent) => void) {
    this.listeners[type] = (this.listeners[type] ?? []).filter(
      (l) => l !== listener,
    );
  }

  dispatchEvent(event: MessageEvent): boolean {
    const handlers = this.listeners[event.type] ?? [];
    handlers.forEach((h) => h(event));
    return true;
  }

  close() {
    this.readyState = 2;
  }

  // Helper for tests to simulate events
  simulateEvent(type: string, data: unknown) {
    const event = new MessageEvent(type, { data: JSON.stringify(data) });
    this.dispatchEvent(event);
  }

  // Helper for tests to simulate errors / disconnects
  simulateError() {
    this.onerror?.(new Event("error"));
  }
}

globalThis.EventSource = MockEventSource as unknown as typeof EventSource;

// Mock scrollIntoView (not implemented in jsdom)
Element.prototype.scrollIntoView = () => {};

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  server.resetHandlers();
  MockEventSource.instances = [];
});
afterAll(() => server.close());
