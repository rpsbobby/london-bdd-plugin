# Qt / C++ Testing Notes — STUB

> **TODO: distil from real usage.** Constraints are discovered, not
> designed. Fill each section the first time the loop hits it in a real
> slice; until then this skeleton keeps the topics in the loop.

## Toolchain
- Unit: GoogleTest + GoogleMock. Mocks ONLY for interaction-is-the-behaviour;
  hand-written fakes otherwise.
- Interfaces: pure-virtual classes with virtual ~dtor; inject by reference
  or std::unique_ptr through constructors.
- TODO: CMake test target layout matching the pipeline's commit stage.

## Headless Qt (acceptance without a display)
- `QT_QPA_PLATFORM=offscreen` for QTest runs; containerisable.
- Acceptance enters at the application-layer boundary — never through
  QWidget code.
- TODO: signal/slot testing patterns (QSignalSpy) and event-loop pitfalls.

## The boundary rule applied to Qt
- QWidget/QML subclasses: rendering + user input forwarding ONLY.
- Business logic in a QWidget = TD entry + a seam candidate.
- TODO: worked example — extracting an application-layer class from a
  legacy QWidget (Sprout Class through a seam).

## Characterisation in C++
- TODO: golden-master patterns for functions with wide output; approval
  files vs inline asserts; link-seam tricks of last resort.

## Windows port
- TODO: platform seams discovered during the port (paths, filesystem,
  process APIs) — each one is a named interface candidate.
