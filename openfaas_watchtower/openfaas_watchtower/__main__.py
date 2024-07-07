"""Main module"""

from openfaas_watchtower.watchtower import (
    run_hey_thread,
    run_fetch_thread,
    check_configuration,
)


def main():
    """Main function of the module"""
    if check_configuration():
        run_hey_thread()
        run_fetch_thread()


if __name__ == "__main__":
    main()
