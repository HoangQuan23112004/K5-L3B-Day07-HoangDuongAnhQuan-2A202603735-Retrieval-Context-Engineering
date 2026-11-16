from .cli import main

if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, RuntimeError, ConnectionError, OSError) as exc:
        raise SystemExit(f'{type(exc).__name__}: {exc}') from None
