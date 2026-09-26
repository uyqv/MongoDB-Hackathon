"""The single long-lived worker. OWNER: Andrew.

CLI (the API spawns this exact command, so keep it stable):
    python -m harness.worker --campaign <campaign_id>
    python -m harness.worker --new --mode {smoke,demo} --max-channels 64 --budget 10

State loop: REHYDRATE -> PLAN -> VALIDATE -> QUEUE -> EXECUTE -> COMMIT -> REHYDRATE,
plus WAITING / PAUSED / FAILED / DONE. Holds no conversation history between steps.
"""


def main() -> None:
    raise NotImplementedError


if __name__ == "__main__":
    main()
