"""Launch the real API-backed local product; no canned starter demonstration."""
import uvicorn


def main():
    uvicorn.run('ekas_press_intelligence.api:create_app', factory=True, host='127.0.0.1', port=18727)


if __name__ == '__main__':
    main()
